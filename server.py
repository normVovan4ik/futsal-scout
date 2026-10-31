"""
Futsal Scout API Server v2.5
Поиск игроков по лигам, поддержка нескольких команд, парсинг дивизионов,
слияние дублирующихся аккаунтов (строго по совпадению ФИО) и SQLite база.
"""

import sys
import json
import re
import time
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import requests as req_lib
from bs4 import BeautifulSoup

import db

# =============================================================================
# Конфигурация источников
# =============================================================================
SOURCES = {
    "liga5x5": {
        "id": "liga5x5",
        "name": "Лига 5х5 (Екатеринбург)",
        "badge_color": "amber",
        "base_url": "https://liga5x5.ru",
        "players_url": "https://liga5x5.ru/participants/players?season_id=all"
    },
    "ligastart": {
        "id": "ligastart",
        "name": "Лига Старт",
        "badge_color": "sky",
        "base_url": "https://ligastart.ru",
        "players_url": "https://ligastart.ru/participants/players?season_id=all"
    },
    "ffge": {
        "id": "ffge",
        "name": "ФФГЭ (Наградион)",
        "badge_color": "emerald",
        "base_url": "https://ffge.nagradion.ru",
        "players_url": "https://ffge.nagradion.ru/tournament-plan"
    }
}

_cache: dict = {}
_cache_ttl = 600  # 10 минут

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def get_soup(url: str) -> BeautifulSoup | None:
    try:
        r = req_lib.get(url, headers=HTTP_HEADERS, timeout=12)
        r.raise_for_status()
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return None


def parse_number(text: str) -> int:
    m = re.match(r"(\d+)", text.strip())
    return int(m.group(1)) if m else 0


def parse_player_teams_detail(player_url: str) -> list[dict]:
    """
    Парсит детальную страницу игрока (/player/{id}) и извлекает команды,
    за которые он выступал, с разбивкой статистики по каждой команде.
    """
    if not player_url:
        return []

    cache_key = f"teams:{player_url}"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return data

    soup = get_soup(player_url)
    if not soup:
        return []

    table = soup.select_one("table")
    teams_stats = {}

    if table:
        for tr in table.select("tr"):
            tds = [td.text.strip() for td in tr.select("td")]
            if len(tds) >= 4:
                t_link = tr.select_one("a[href*='/team/']")
                team_name = t_link.text.strip() if t_link else (
                    tds[0] if len(tds[0]) > 2 and not any(c.isdigit() for c in tds[0]) else ""
                )

                # Проверяем строку команды: tds[1] - матчи, tds[2] - голы
                if team_name and re.match(r"^\d+$", tds[1]) and re.match(r"^\d+", tds[2]):
                    matches = int(tds[1])
                    goals = parse_number(tds[2])
                    assists = int(tds[3]) if len(tds) > 3 and tds[3].isdigit() else 0
                    yc = int(tds[4]) if len(tds) > 4 and tds[4].isdigit() else 0
                    rc = int(tds[5]) if len(tds) > 5 and tds[5].isdigit() else 0

                    if team_name not in teams_stats:
                        teams_stats[team_name] = {
                            "team_name": team_name,
                            "matches": 0,
                            "goals": 0,
                            "assists": 0,
                            "yellow_cards": 0,
                            "red_cards": 0
                        }
                    ts = teams_stats[team_name]
                    ts["matches"] += matches
                    ts["goals"] += goals
                    ts["assists"] += assists
                    ts["yellow_cards"] += yc
                    ts["red_cards"] += rc

    # Если через таблицу не нашли, ищем упоминания команд в ссылках
    if not teams_stats:
        found_names = set()
        for a in soup.select("a[href*='/team/']"):
            tname = a.text.strip()
            if tname and len(tname) > 1 and tname not in found_names:
                found_names.add(tname)
                teams_stats[tname] = {
                    "team_name": tname,
                    "matches": 0,
                    "goals": 0,
                    "assists": 0,
                    "yellow_cards": 0,
                    "red_cards": 0
                }

    res = list(teams_stats.values())
    _cache[cache_key] = (res, time.time())
    return res


def scrape_league_table(source_key: str) -> list[dict]:
    """Парсит таблицу бомбардиров для LigaStart / Liga5x5."""
    if source_key not in SOURCES:
        return []

    src = SOURCES[source_key]
    url = src["players_url"]

    if url in _cache:
        data, ts = _cache[url]
        if time.time() - ts < _cache_ttl:
            return data

    soup = get_soup(url)
    if not soup:
        return []

    players = []
    table = soup.select_one("table")
    if not table:
        return []

    headers = [th.text.strip() for th in table.select("th")]

    col = {}
    seen_g = False
    for i, h in enumerate(headers):
        if h == "#":
            col["rank"] = i
        elif "Игрок" in h:
            col["name"] = i
        elif h == "И":
            col["matches"] = i
        elif h.startswith("Г") and not seen_g:
            col["goals"] = i
            seen_g = True
        elif h == "П":
            col["assists"] = i
        elif h == "Г+П":
            col["total_pts"] = i
        elif "ЖК" in h:
            col["yellow_cards"] = i
        elif "КК" in h:
            col["red_cards"] = i
        elif "Лм" in h or "MVP" in h:
            col["mvp"] = i

    for row in table.select("tbody tr"):
        cells = row.select("td")
        if len(cells) < 3:
            continue

        def cell_val(key, default=0):
            if key in col and col[key] < len(cells):
                txt = cells[col[key]].text.strip()
                return parse_number(txt)
            return default

        name = ""
        player_id = None
        player_url = None
        if "name" in col and col["name"] < len(cells):
            name_cell = cells[col["name"]]
            name = name_cell.text.strip()
            link = name_cell.select_one("a")
            if link:
                href = link["href"]
                player_url = urljoin(src["base_url"], href)
                m = re.search(r"/player/(\d+)", href)
                if m:
                    player_id = int(m.group(1))

        if not name or len(name) < 2:
            continue

        goals_raw = cells[col["goals"]].text.strip() if "goals" in col and col["goals"] < len(cells) else "0"
        goals = parse_number(goals_raw)

        players.append({
            "source_id": source_key,
            "source_name": src["name"],
            "rank": cell_val("rank"),
            "name": name,
            "player_id": player_id,
            "player_url": player_url,
            "matches": cell_val("matches"),
            "goals": goals,
            "assists": cell_val("assists"),
            "total_pts": cell_val("total_pts"),
            "yellow_cards": cell_val("yellow_cards"),
            "red_cards": cell_val("red_cards"),
            "mvp_count": cell_val("mvp"),
            "teams": []  # Загружается по требованию или при поиске
        })

    _cache[url] = (players, time.time())
    print(f"Спарсено из {src['name']}: {len(players)} игроков")
    return players


def scrape_ffge_data() -> list[dict]:
    """Парсинг турниров и игроков с ffge.nagradion.ru."""
    cache_key = "ffge_all"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return data

    players = []
    _cache[cache_key] = (players, time.time())
    return players


# =============================================================================
# Многосайтовый поиск и слияние аккаунтов
# =============================================================================
def search_all_sources(query: str) -> list[dict]:
    """
    Ищет по всем лигам. Возвращает сгруппированных по ФИО игроков,
    где для каждого человека видны все его отдельные аккаунты, команды
    и возможность слияния.
    """
    q = query.strip().lower()
    if not q:
        return []

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_liga5x5 = executor.submit(scrape_league_table, "liga5x5")
        f_ligastart = executor.submit(scrape_league_table, "ligastart")
        f_ffge = executor.submit(scrape_ffge_data)

        liga5x5_players = f_liga5x5.result()
        ligastart_players = f_ligastart.result()
        ffge_players = f_ffge.result()

    all_raw = liga5x5_players + ligastart_players + ffge_players

    # Фильтруем по поисковому запросу
    q_tokens = q.split()
    matched = []
    for p in all_raw:
        p_name_low = p["name"].lower()
        if all(token in p_name_low for token in q_tokens):
            matched.append(p)

    # Загружаем детальную информацию о командах для совпавших игроков
    def enrich_player(p):
        if p.get("player_url"):
            try:
                teams = parse_player_teams_detail(p["player_url"])
                p["teams"] = teams
            except Exception:
                p["teams"] = []
        return p

    with ThreadPoolExecutor(max_workers=5) as executor:
        matched = list(executor.map(enrich_player, matched))

    # Группируем по каноническому имени (Фамилия Имя)
    grouped: dict[str, dict] = {}

    for p in matched:
        canonical_name = " ".join(p["name"].split())

        if canonical_name not in grouped:
            grouped[canonical_name] = {
                "name": canonical_name,
                "accounts": [],          # Список всех отдельных аккаунтов этого человека
                "all_teams": {},         # Сводная таблица по всем командам
                "sources_found": [],
                "sources_data": {},
                "total_matches": 0,
                "total_goals": 0,
                "total_assists": 0,
                "total_yellow_cards": 0,
                "total_red_cards": 0,
                "total_mvp": 0,
                "total_pts": 0,
                "sample_url": p.get("player_url")
            }

        g = grouped[canonical_name]
        src_name = p["source_name"]
        src_id = p["source_id"]

        if src_name not in g["sources_found"]:
            g["sources_found"].append(src_name)

        # Добавляем аккаунт в список аккаунтов этого игрока
        g["accounts"].append({
            "account_id": p.get("player_id"),
            "player_url": p.get("player_url"),
            "source_id": src_id,
            "source_name": src_name,
            "matches": p.get("matches", 0),
            "goals": p.get("goals", 0),
            "assists": p.get("assists", 0),
            "yellow_cards": p.get("yellow_cards", 0),
            "red_cards": p.get("red_cards", 0),
            "mvp_count": p.get("mvp_count", 0),
            "teams": p.get("teams", [])
        })

        # Добавляем команды в общий список
        for t in p.get("teams", []):
            tname = t["team_name"]
            if tname not in g["all_teams"]:
                g["all_teams"][tname] = {
                    "team_name": tname,
                    "matches": 0,
                    "goals": 0,
                    "assists": 0,
                    "yellow_cards": 0,
                    "red_cards": 0
                }
            g["all_teams"][tname]["matches"] += t.get("matches", 0)
            g["all_teams"][tname]["goals"] += t.get("goals", 0)
            g["all_teams"][tname]["assists"] += t.get("assists", 0)
            g["all_teams"][tname]["yellow_cards"] += t.get("yellow_cards", 0)
            g["all_teams"][tname]["red_cards"] += t.get("red_cards", 0)

        # Суммируем в разрезе источника
        if src_id not in g["sources_data"]:
            g["sources_data"][src_id] = {
                "source_id": src_id,
                "source_name": src_name,
                "badge_color": SOURCES[src_id]["badge_color"],
                "matches": 0,
                "goals": 0,
                "assists": 0,
                "total_pts": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "mvp_count": 0,
                "player_url": p.get("player_url")
            }

        s_entry = g["sources_data"][src_id]
        s_entry["matches"] += p.get("matches", 0)
        s_entry["goals"] += p.get("goals", 0)
        s_entry["assists"] += p.get("assists", 0)
        s_entry["total_pts"] += p.get("total_pts", 0)
        s_entry["yellow_cards"] += p.get("yellow_cards", 0)
        s_entry["red_cards"] += p.get("red_cards", 0)
        s_entry["mvp_count"] += p.get("mvp_count", 0)
        if not s_entry.get("player_url"):
            s_entry["player_url"] = p.get("player_url")

        # Суммарные числа
        g["total_matches"] += p.get("matches", 0)
        g["total_goals"] += p.get("goals", 0)
        g["total_assists"] += p.get("assists", 0)
        g["total_yellow_cards"] += p.get("yellow_cards", 0)
        g["total_red_cards"] += p.get("red_cards", 0)
        g["total_mvp"] += p.get("mvp_count", 0)
        g["total_pts"] += p.get("total_pts", 0)

    result = list(grouped.values())
    result.sort(key=lambda x: (x["total_goals"] + x["total_assists"]), reverse=True)

    return result


# =============================================================================
# FastAPI приложение
# =============================================================================
app = FastAPI(title="Futsal Scout Hub", version="2.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

STATIC_DIR = Path(__file__).parent


@app.get("/")
def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/app.js")
def get_app_js():
    return FileResponse(str(STATIC_DIR / "app.js"), media_type="application/javascript")


@app.get("/style.css")
def get_style_css():
    return FileResponse(str(STATIC_DIR / "style.css"), media_type="text/css")


@app.get("/favicon.ico")
def get_favicon():
    return FileResponse(str(STATIC_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/sources")
def get_sources():
    return list(SOURCES.values())


@app.get("/api/search")
def search_endpoint(q: str = Query(..., min_length=2)):
    results = search_all_sources(q)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }


@app.get("/api/player_teams")
def player_teams_endpoint(url: str = Query(...)):
    """Получить список команд для конкретного игрока."""
    teams = parse_player_teams_detail(url)
    return {"url": url, "teams": teams}


@app.post("/api/merge_accounts")
def merge_accounts_endpoint(accounts: list[dict] = Body(...)):
    """
    Слияние нескольких аккаунтов одного игрока.
    СТРОГОЕ ПРАВИЛО: Имена и фамилии во всех объединяемых аккаунтах должны совпадать!
    """
    if len(accounts) < 2:
        raise HTTPException(400, "Для слияния необходимо выбрать как минимум 2 аккаунта!")

    # Проверка на совпадение ФИО
    names = set(" ".join(a.get("name", "").strip().split()).lower() for a in accounts)
    if len(names) > 1:
        raise HTTPException(
            400,
            f"Слияние запрещено! Аккаунты принадлежат разным людям: {list(names)}. Объединять можно только аккаунты с одинаковым именем и фамилией."
        )

    canonical_name = accounts[0]["name"]
    merged = {
        "name": canonical_name,
        "is_merged": True,
        "merged_accounts_count": len(accounts),
        "total_matches": 0,
        "total_goals": 0,
        "total_assists": 0,
        "total_yellow_cards": 0,
        "total_red_cards": 0,
        "total_mvp": 0,
        "total_pts": 0,
        "all_teams": {},
        "sources_data": {}
    }

    for a in accounts:
        merged["total_matches"] += a.get("matches", 0)
        merged["total_goals"] += a.get("goals", 0)
        merged["total_assists"] += a.get("assists", 0)
        merged["total_yellow_cards"] += a.get("yellow_cards", 0)
        merged["total_red_cards"] += a.get("red_cards", 0)
        merged["total_mvp"] += a.get("mvp_count", 0)
        merged["total_pts"] += (a.get("goals", 0) + a.get("assists", 0))

        # Объединяем команды
        for t in a.get("teams", []):
            tname = t["team_name"]
            if tname not in merged["all_teams"]:
                merged["all_teams"][tname] = {
                    "team_name": tname,
                    "matches": 0,
                    "goals": 0,
                    "assists": 0,
                    "yellow_cards": 0,
                    "red_cards": 0
                }
            merged["all_teams"][tname]["matches"] += t.get("matches", 0)
            merged["all_teams"][tname]["goals"] += t.get("goals", 0)
            merged["all_teams"][tname]["assists"] += t.get("assists", 0)
            merged["all_teams"][tname]["yellow_cards"] += t.get("yellow_cards", 0)
            merged["all_teams"][tname]["red_cards"] += t.get("red_cards", 0)

    return {"status": "ok", "merged_player": merged}


@app.get("/api/players")
def get_players_endpoint(source: str = Query("liga5x5"), limit: int = Query(100)):
    players = scrape_league_table(source)
    return {"source": source, "count": len(players[:limit]), "players": players[:limit]}


@app.get("/api/favorites")
def get_favorites():
    return db.get_all_favorites()


@app.post("/api/favorites")
def save_favorite_endpoint(data: dict = Body(...)):
    fav_id = db.save_favorite(data)
    return {"status": "ok", "id": fav_id, "message": "Игрок сохранен в базу!"}


@app.delete("/api/favorites/{fav_id}")
def delete_favorite_endpoint(fav_id: int):
    deleted = db.delete_favorite(fav_id)
    if not deleted:
        raise HTTPException(404, "Игрок не найден в базе")
    return {"status": "ok", "deleted": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
