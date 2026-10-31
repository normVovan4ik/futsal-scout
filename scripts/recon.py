"""
Разведочный скрипт: изучаем структуру трёх футзальных сайтов.
Запуск: python scripts/recon.py
"""
import sys
import json
import re
from urllib.parse import urljoin, urlparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Устанавливаем зависимости...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "lxml"])
    import requests
    from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

SITES = [
    "https://ffge.nagradion.ru/",
    "https://ligastart.ru/",
    "https://liga5x5.ru/"
]

# Ключевые слова для поиска разделов статистики
STAT_KEYWORDS = [
    "player", "person", "игрок",
    "team", "команда",
    "scorer", "бомбардир",
    "statistic", "stat", "статистик",
    "tournament", "league", "турнир", "лига",
    "profile", "профил"
]


def analyze_site(base_url: str) -> dict:
    domain = urlparse(base_url).netloc
    report = {
        "domain": domain,
        "base_url": base_url,
        "title": "",
        "tech": [],
        "robots_txt": "",
        "sitemap_hints": [],
        "key_links": [],
        "all_path_patterns": [],
        "tables": [],
        "api_hints": [],
        "error": None
    }

    print(f"\n{'='*60}")
    print(f"  Анализ: {base_url}")
    print(f"{'='*60}")

    # 1. Главная страница
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        report["title"] = soup.title.text.strip() if soup.title else "N/A"
        print(f"  ✅ Title: {report['title']}")

        # Определяем технологии
        if "react" in r.text.lower() or "ReactDOM" in r.text:
            report["tech"].append("React (JS рендеринг)")
        if "vue" in r.text.lower() and "vue.js" in r.text.lower():
            report["tech"].append("Vue.js")
        if "next" in r.text.lower() and "__NEXT_DATA__" in r.text:
            report["tech"].append("Next.js")
            # Пробуем вытащить данные из Next.js
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if match:
                try:
                    next_data = json.loads(match.group(1))
                    report["api_hints"].append(f"Next.js __NEXT_DATA__ найден: {list(next_data.keys())}")
                except Exception:
                    pass
        if "django" in r.text.lower() or "csrfmiddlewaretoken" in r.text.lower():
            report["tech"].append("Django (Python backend)")
        if "laravel" in r.text.lower():
            report["tech"].append("Laravel (PHP)")
        if "__INITIAL_STATE__" in r.text or "window.__data" in r.text:
            report["tech"].append("SSR с preloaded state")

        print(f"  🔧 Технологии: {report['tech'] or ['Обычный HTML/SSR']}")

        # Собираем все внутренние ссылки
        all_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(base_url, href)
            if domain in full:
                all_links.append(full)

        # Паттерны URL (первые 3 сегмента пути)
        patterns = set()
        for link in all_links:
            path = urlparse(link).path
            parts = [p for p in path.split("/") if p]
            if parts:
                pattern = "/" + "/".join(parts[:2]) + "/"
                patterns.add(pattern)

        report["all_path_patterns"] = sorted(patterns)[:40]

        # Ключевые ссылки (по ключевым словам)
        key_links = {}
        for a in soup.find_all("a", href=True):
            text = (a.text or "").strip().lower()
            href = a["href"]
            full = urljoin(base_url, href)
            for kw in STAT_KEYWORDS:
                if kw in text or kw in href.lower():
                    key_links[full] = text[:60]
                    break

        report["key_links"] = [{"url": k, "text": v} for k, v in list(key_links.items())[:20]]

        # Таблицы на главной
        for table in soup.find_all("table")[:5]:
            headers = [th.text.strip() for th in table.find_all("th")]
            first_row = [td.text.strip() for td in table.find_all("tr")[1].find_all("td")] if len(table.find_all("tr")) > 1 else []
            report["tables"].append({
                "class": table.get("class"),
                "id": table.get("id"),
                "headers": headers[:10],
                "first_row_sample": first_row[:10]
            })

        print(f"  🔗 Ключевых ссылок найдено: {len(report['key_links'])}")
        print(f"  📊 Таблиц найдено: {len(report['tables'])}")
        print(f"  📁 Паттернов путей: {len(report['all_path_patterns'])}")
        if report["all_path_patterns"]:
            print(f"  📁 Примеры: {report['all_path_patterns'][:10]}")

    except Exception as e:
        report["error"] = str(e)
        print(f"  ❌ Ошибка главной: {e}")
        return report

    # 2. robots.txt
    try:
        robots_url = urljoin(base_url, "/robots.txt")
        rb = requests.get(robots_url, headers=HEADERS, timeout=10)
        if rb.status_code == 200:
            report["robots_txt"] = rb.text[:800]
            print(f"\n  📋 robots.txt (первые строки):")
            for line in rb.text.split("\n")[:15]:
                if line.strip():
                    print(f"    {line}")
    except Exception as e:
        print(f"  ⚠️  robots.txt недоступен: {e}")

    # 3. sitemap.xml — ищем паттерны URL игроков/команд
    try:
        sitemap_url = urljoin(base_url, "/sitemap.xml")
        sm = requests.get(sitemap_url, headers=HEADERS, timeout=10)
        if sm.status_code == 200:
            sm_soup = BeautifulSoup(sm.text, "xml")
            locs = [loc.text for loc in sm_soup.find_all("loc")][:30]
            # Фильтруем по ключевым словам
            player_urls = [l for l in locs if any(kw in l for kw in ["player", "person", "team", "league", "tournament"])]
            report["sitemap_hints"] = player_urls[:20]
            print(f"\n  🗺️  Sitemap: {len(locs)} URL, интересных: {len(player_urls)}")
            for url in player_urls[:5]:
                print(f"    {url}")
    except Exception as e:
        print(f"  ⚠️  Sitemap недоступен: {e}")

    # 4. Пробуем найти страницу бомбардиров / статистики
    test_stat_urls = []
    # Используем паттерны из ссылок на главной
    for link_info in report["key_links"]:
        url = link_info["url"]
        if any(kw in url.lower() for kw in ["scorer", "stat", "bomber", "игрок", "бомбар", "player"]):
            test_stat_urls.append(url)

    # Также пробуем типовые пути
    typical_paths = [
        "/players/", "/scorers/", "/statistics/", "/teams/",
        "/tournament/", "/tournaments/", "/leagues/", "/league/",
        "/person/", "/persons/"
    ]
    for path in typical_paths:
        test_stat_urls.append(urljoin(base_url, path))

    stat_pages = {}
    for url in list(dict.fromkeys(test_stat_urls))[:8]:  # убираем дубли
        try:
            rs = requests.get(url, headers=HEADERS, timeout=10)
            if rs.status_code == 200:
                s2 = BeautifulSoup(rs.text, "lxml")
                tables = s2.find_all("table")
                player_links = [
                    urljoin(url, a["href"])
                    for a in s2.find_all("a", href=True)
                    if any(kw in a["href"].lower() for kw in ["player", "person", "profile"])
                ]
                all_internal = [
                    urljoin(url, a["href"])
                    for a in s2.find_all("a", href=True)
                    if domain in urljoin(url, a["href"])
                ]

                stat_pages[url] = {
                    "status": rs.status_code,
                    "title": s2.title.text.strip() if s2.title else "",
                    "tables_count": len(tables),
                    "player_links_sample": player_links[:5],
                    "table_headers": [
                        [th.text.strip() for th in t.find_all("th")][:8]
                        for t in tables[:3]
                    ]
                }
                print(f"\n  📄 [{rs.status_code}] {url}")
                print(f"     Таблиц: {len(tables)}, ссылок на игроков: {len(player_links)}")
                if tables:
                    for i, t in enumerate(tables[:2]):
                        hdrs = [th.text.strip() for th in t.find_all("th")]
                        print(f"     Таблица {i+1} заголовки: {hdrs[:8]}")
                if player_links:
                    print(f"     Примеры ссылок на игроков: {player_links[:3]}")
        except Exception as e:
            pass

    report["stat_pages"] = stat_pages

    # 5. Если нашли ссылки на игроков — заходим на первую и смотрим HTML
    all_player_links = []
    for page_data in stat_pages.values():
        all_player_links.extend(page_data.get("player_links_sample", []))

    if all_player_links:
        player_url = all_player_links[0]
        try:
            rp = requests.get(player_url, headers=HEADERS, timeout=10)
            if rp.status_code == 200:
                sp = BeautifulSoup(rp.text, "lxml")
                # Пробуем найти имя
                name_candidates = []
                for tag in ["h1", "h2", ".player-name", ".person-name", ".player__name"]:
                    el = sp.select_one(tag)
                    if el:
                        name_candidates.append(f"{tag}: {el.text.strip()[:50]}")

                # Все таблицы на странице игрока
                player_tables = []
                for t in sp.find_all("table")[:5]:
                    headers = [th.text.strip() for th in t.find_all("th")][:10]
                    rows = []
                    for tr in t.find_all("tr")[1:3]:
                        row = [td.text.strip() for td in tr.find_all("td")][:10]
                        if row:
                            rows.append(row)
                    player_tables.append({"headers": headers, "sample_rows": rows})

                report["player_page_sample"] = {
                    "url": player_url,
                    "name_candidates": name_candidates,
                    "tables": player_tables
                }
                print(f"\n  👤 Страница игрока: {player_url}")
                print(f"     Имя кандидаты: {name_candidates}")
                for i, pt in enumerate(player_tables):
                    print(f"     Таблица {i+1}: заголовки={pt['headers']}")
                    for row in pt["sample_rows"]:
                        print(f"       Строка: {row}")
        except Exception as e:
            print(f"  ⚠️  Страница игрока недоступна: {e}")

    return report


def main():
    print("\n🔍 РАЗВЕДКА ФУТЗАЛЬНЫХ САЙТОВ")
    print("=" * 60)
    all_reports = {}

    for site in SITES:
        report = analyze_site(site)
        all_reports[site] = report

    # Сохраняем полный отчёт в JSON
    output_path = "scripts/recon_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n\n✅ Полный отчёт сохранён: {output_path}")
    print("\n📌 КРАТКИЕ ИТОГИ:")
    for site, data in all_reports.items():
        print(f"\n  {data['domain']}:")
        if data.get("error"):
            print(f"    ❌ Ошибка: {data['error']}")
        else:
            print(f"    📁 Паттерны путей: {data['all_path_patterns'][:6]}")
            if data.get("sitemap_hints"):
                print(f"    🗺️  Из sitemap: {data['sitemap_hints'][:3]}")
            if data.get("player_page_sample"):
                print(f"    👤 Игрок URL: {data['player_page_sample']['url']}")


if __name__ == "__main__":
    main()
