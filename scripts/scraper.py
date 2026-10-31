"""
Futsal Scout Scraper
Парсер для ligastart.ru и liga5x5.ru (и других сайтов на той же платформе LigaStart).

Поддерживаемые URL:
  - /participants/players               — таблица всех бомбардиров сезона
  - /participants/players?season_id=XXX — конкретный сезон
  - /player/{id}                        — профиль конкретного игрока
  - /team/{id}                          — страница команды

Использование:
  python scripts/scraper.py --url https://liga5x5.ru/participants/players
  python scripts/scraper.py --url https://ligastart.ru/player/10338279
  python scripts/scraper.py --url https://liga5x5.ru/team/123456
"""

import sys
import json
import re
import argparse
import time
from urllib.parse import urljoin, urlparse, urlencode, parse_qs

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://liga5x5.ru/"
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    """Загружает страницу и возвращает BeautifulSoup объект."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=15)
            r.raise_for_status()
            r.encoding = "utf-8"
            return BeautifulSoup(r.text, "lxml")
        except requests.RequestException as e:
            if attempt < retries - 1:
                print(f"  Попытка {attempt+1} не удалась: {e}. Повтор...")
                time.sleep(2)
            else:
                print(f"  Ошибка загрузки {url}: {e}")
                return None


def parse_number(text: str) -> int:
    """Извлекает число из текста типа '63 (3)' -> 63."""
    match = re.match(r"(\d+)", text.strip())
    return int(match.group(1)) if match else 0


def parse_float(text: str) -> float:
    """Парсит число с плавающей точкой."""
    try:
        return float(text.strip().replace(",", "."))
    except Exception:
        return 0.0


def scrape_players_table(url: str) -> list[dict]:
    """
    Парсит таблицу бомбардиров /participants/players.
    Возвращает список игроков со статистикой.

    Колонки таблицы:
    #  | Игрок | И | Г (Пн., 10м) | Ср. | П | Ср. | Г+П | ЖК | КК
    """
    print(f"\nПарсим таблицу игроков: {url}")
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    players = []

    # Получаем список доступных сезонов
    soup = get_page(url)
    if not soup:
        return []

    # Определяем доступные сезоны из select/ссылок
    seasons = {}
    season_links = soup.select("a[href*='season_id']")
    for a in season_links:
        href = a["href"]
        m = re.search(r"season_id=(\w+)", href)
        if m:
            seasons[m.group(1)] = a.text.strip()

    # Добавляем текущую (без параметра)
    seasons["current"] = "Текущий сезон"
    print(f"  Найдено сезонов: {list(seasons.values())[:5]}")

    # Парсим основную таблицу (текущий сезон)
    table = soup.select_one("table")
    if not table:
        print("  Таблица не найдена!")
        return []

    headers_raw = [th.text.strip() for th in table.select("th")]
    print(f"  Заголовки: {headers_raw}")

    # Определяем индексы нужных колонок
    col_map = {}
    for i, h in enumerate(headers_raw):
        h_low = h.lower()
        if h == "#":
            col_map["rank"] = i
        elif "игрок" in h_low or "player" in h_low:
            col_map["name"] = i
        elif h == "И":
            col_map["matches"] = i
        elif h.startswith("Г"):
            col_map["goals"] = i
        elif h == "П":
            col_map["assists"] = i
        elif h == "Г+П":
            col_map["total_pts"] = i
        elif "ЖК" in h or "жк" in h_low:
            col_map["yellow_cards"] = i
        elif "КК" in h or "кк" in h_low:
            col_map["red_cards"] = i

    print(f"  Карта колонок: {col_map}")

    rows = table.select("tbody tr")
    print(f"  Строк в таблице: {len(rows)}")

    for row in rows:
        cells = row.select("td")
        if len(cells) < 3:
            continue

        player = {
            "rank": 0,
            "name": "",
            "player_url": None,
            "player_id": None,
            "matches": 0,
            "goals": 0,
            "assists": 0,
            "total_pts": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "source_url": url
        }

        # Ранк
        if "rank" in col_map and col_map["rank"] < len(cells):
            player["rank"] = parse_number(cells[col_map["rank"]].text)

        # Имя + ссылка на профиль
        if "name" in col_map and col_map["name"] < len(cells):
            name_cell = cells[col_map["name"]]
            player["name"] = name_cell.text.strip()
            link = name_cell.select_one("a")
            if link:
                full_url = urljoin(base, link["href"])
                player["player_url"] = full_url
                m = re.search(r"/player/(\d+)", full_url)
                if m:
                    player["player_id"] = int(m.group(1))

        # Матчи
        if "matches" in col_map and col_map["matches"] < len(cells):
            player["matches"] = parse_number(cells[col_map["matches"]].text)

        # Голы (формат "63 (3)" — второе число в скобках это голы с пенальти)
        if "goals" in col_map and col_map["goals"] < len(cells):
            goals_text = cells[col_map["goals"]].text.strip()
            player["goals"] = parse_number(goals_text)
            # Голы с пенальти/штрафных
            pen_match = re.search(r"\((\d+)\)", goals_text)
            player["goals_from_penalty"] = int(pen_match.group(1)) if pen_match else 0

        # Ассисты
        if "assists" in col_map and col_map["assists"] < len(cells):
            player["assists"] = parse_number(cells[col_map["assists"]].text)

        # Г+П
        if "total_pts" in col_map and col_map["total_pts"] < len(cells):
            player["total_pts"] = parse_number(cells[col_map["total_pts"]].text)

        # ЖК
        if "yellow_cards" in col_map and col_map["yellow_cards"] < len(cells):
            player["yellow_cards"] = parse_number(cells[col_map["yellow_cards"]].text)

        # КК
        if "red_cards" in col_map and col_map["red_cards"] < len(cells):
            player["red_cards"] = parse_number(cells[col_map["red_cards"]].text)

        if player["name"]:
            players.append(player)

    print(f"  Спарсено игроков: {len(players)}")
    return players


def scrape_player_profile(url: str) -> dict | None:
    """
    Парсит страницу профиля конкретного игрока /player/{id}.
    Возвращает словарь с детальной статистикой по сезонам.
    """
    print(f"\nПарсим профиль игрока: {url}")
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    soup = get_page(url)
    if not soup:
        return None

    player_id_match = re.search(r"/player/(\d+)", url)
    player_id = int(player_id_match.group(1)) if player_id_match else None

    profile = {
        "player_id": player_id,
        "player_url": url,
        "name": "",
        "team": "",
        "team_url": None,
        "team_id": None,
        "photo_url": None,
        "position": "",
        "seasons": [],  # Статистика по каждому сезону
        "career_totals": {}  # Суммарная карьерная статистика
    }

    # Имя игрока
    for selector in ["h1", ".player-name", ".person-name", ".player__name", ".title"]:
        el = soup.select_one(selector)
        if el and len(el.text.strip()) > 2:
            profile["name"] = el.text.strip()
            break

    # Команда
    team_link = None
    for link in soup.select("a[href*='/team/']"):
        team_link = link
        break

    if team_link:
        profile["team"] = team_link.text.strip()
        profile["team_url"] = urljoin(base, team_link["href"])
        m = re.search(r"/team/(\d+)", team_link["href"])
        if m:
            profile["team_id"] = int(m.group(1))

    # Фото
    for img_sel in [".player-photo img", ".person-photo img", ".player__photo", "img.avatar"]:
        img = soup.select_one(img_sel)
        if img and img.get("src"):
            profile["photo_url"] = urljoin(base, img["src"])
            break

    # Амплуа/позиция
    for text_el in soup.find_all(string=re.compile(r"(нападающ|защитник|вратарь|полузащитник|форвард|пивот|ала|фиксо)", re.I)):
        profile["position"] = text_el.strip()
        break

    # Таблицы статистики по сезонам
    tables = soup.select("table")
    for table in tables:
        headers = [th.text.strip() for th in table.select("th")]
        if not headers:
            continue

        rows = table.select("tbody tr")
        season_data_list = []

        for row in rows:
            cells = row.select("td")
            if not cells:
                continue

            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = cell.text.strip()
                else:
                    row_data[f"col_{i}"] = cell.text.strip()
            season_data_list.append(row_data)

        if season_data_list:
            profile["seasons"].append({
                "table_headers": headers,
                "rows": season_data_list
            })

    # Суммарная статистика из карточек/блоков
    # Ищем блоки типа <div class="stat-card"><span class="value">23</span><span>Голы</span></div>
    stat_blocks = {}
    for div in soup.find_all("div"):
        spans = div.find_all("span")
        if len(spans) >= 2:
            for i, span in enumerate(spans):
                value_text = spans[0].text.strip()
                label_text = spans[-1].text.strip().lower()
                if re.match(r"^\d+$", value_text) and any(w in label_text for w in ["гол", "матч", "ассист", "пас", "карт"]):
                    stat_blocks[label_text] = int(value_text)

    if stat_blocks:
        profile["career_totals"] = stat_blocks

    print(f"  Игрок: {profile['name']} | Команда: {profile['team']}")
    print(f"  Таблиц со статой: {len(profile['seasons'])}")
    return profile


def scrape_team(url: str) -> dict | None:
    """Парсит страницу команды: состав и статистика игроков."""
    print(f"\nПарсим команду: {url}")
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    soup = get_page(url)
    if not soup:
        return None

    team = {
        "team_url": url,
        "name": "",
        "players": []
    }

    for selector in ["h1", ".team-name", ".team__name"]:
        el = soup.select_one(selector)
        if el and len(el.text.strip()) > 1:
            team["name"] = el.text.strip()
            break

    for a in soup.select("a[href*='/player/']"):
        href = a["href"]
        full_url = urljoin(base, href)
        m = re.search(r"/player/(\d+)", full_url)
        if m:
            team["players"].append({
                "name": a.text.strip(),
                "player_id": int(m.group(1)),
                "player_url": full_url
            })

    # Убираем дубли
    seen = set()
    unique_players = []
    for p in team["players"]:
        if p["player_id"] not in seen:
            seen.add(p["player_id"])
            unique_players.append(p)
    team["players"] = unique_players

    print(f"  Команда: {team['name']} | Игроков в составе: {len(team['players'])}")
    return team


def detect_url_type(url: str) -> str:
    """Определяет тип страницы по URL."""
    if "/participants/players" in url:
        return "players_table"
    elif re.search(r"/player/\d+", url):
        return "player_profile"
    elif re.search(r"/team/\d+", url):
        return "team"
    elif "ligastart.ru" in url or "liga5x5.ru" in url or "nagradion.ru" in url:
        return "players_table"  # по умолчанию пробуем таблицу
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Futsal Scout Scraper")
    parser.add_argument("--url", required=True, help="URL для парсинга")
    parser.add_argument("--output", default="scripts/scraped_data.json", help="Файл для сохранения результата")
    parser.add_argument("--limit", type=int, default=50, help="Лимит игроков (для таблицы бомбардиров)")
    args = parser.parse_args()

    url_type = detect_url_type(args.url)
    print(f"Тип страницы: {url_type}")

    result = None

    if url_type == "players_table":
        players = scrape_players_table(args.url)
        players = players[:args.limit]
        result = {
            "type": "players_table",
            "source": args.url,
            "count": len(players),
            "players": players
        }

        print("\n--- ТОП-10 ИГРОКОВ ---")
        for p in players[:10]:
            print(f"  {p['rank']:>2}. {p['name']:<35} {p['matches']}и  {p['goals']}г  {p['assists']}п  ЖК:{p['yellow_cards']}")

    elif url_type == "player_profile":
        profile = scrape_player_profile(args.url)
        result = {"type": "player_profile", "source": args.url, "player": profile}

    elif url_type == "team":
        team = scrape_team(args.url)
        result = {"type": "team", "source": args.url, "team": team}

    else:
        print(f"Неизвестный тип URL. Попробуем как таблицу игроков...")
        players = scrape_players_table(args.url)
        result = {"type": "players_table", "source": args.url, "players": players}

    # Сохраняем результат
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nРезультат сохранён: {args.output}")
    return result


if __name__ == "__main__":
    main()
