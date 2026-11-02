"""
Futsal Scout API Server v4.0
Поиск игроков и команд по всем 3 сайтам: Лига 5х5, Лига Старт и ФФГЭ Наградион.
Поддержка живого поиска по ФИО, слияние дублирующихся аккаунтов,
разбивка статистики по всем командам и дивизионам, поиск команд, загрузка кастомных аватаров и SQLite база.
"""

import sys
import json
import re
import time
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, HTTPException, Query, Body, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
        return None


def parse_number(text: str) -> int:
    m = re.match(r"(\d+)", text.strip())
    return int(m.group(1)) if m else 0


def get_ffge_futsal_tournaments(limit=40) -> list[tuple]:
    """Динамически получает список актуальных футзальных турниров ФФГЭ с календаря."""
    cache_key = "ffge:tournaments_plan"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < 1800:
            return data[:limit]

    url = "https://ffge.nagradion.ru/tournament-plan"
    soup = get_soup(url)
    if not soup:
        # Fallback на известные ключевые турниры
        return [
            ("46382", "Финал Чемпионата Екатеринбурга 5х5 (2026)"),
            ("46309", "Чемпионат города 1 Дивизион (26/27)"),
            ("46310", "Чемпионат города 2 Дивизион (26/27)"),
            ("46315", "Чемпионат города 3 Дивизион (26/27)"),
            ("46316", "Чемпионат города 4 Дивизион (26/27)"),
            ("45832", "Первенство Чкаловского района 5х5 (2026)"),
            ("45862", "Первенство Кировского района 5х5 (2026)"),
            ("45884", "Первенство Железнодорожного района 5х5 (2026)"),
            ("45993", "Первенство Академического района 5х5 (2026)"),
            ("45914", "Турнир по мини-футболу 5х5 лето 2026")
        ]

    futsal_t = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"/tournament(\d+)", a["href"])
        if m:
            tid = m.group(1)
            name = a.text.strip()
            if name and len(name) > 3 and not name.startswith("Шахматка"):
                nl = name.lower()
                if any(w in nl for w in ["футзал", "мини-футбол", "5х5", "5 на 5", "6х6", "7х7", "чемпионат", "первенство", "кубок", "лига"]):
                    if not any(t[0] == tid for t in futsal_t):
                        futsal_t.append((tid, name))

    _cache[cache_key] = (futsal_t, time.time())
    return futsal_t[:limit]


def parse_player_teams_detail(player_url: str) -> list[dict]:
    """Парсит детальную страницу игрока (/player/{id}) и извлекает команды."""
    if not player_url:
        return []

    cache_key = f"teams:{player_url}"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return data

    if "nagradion.ru" in player_url:
        prof = parse_ffge_player_profile(player_url)
        if prof and prof.get("teams"):
            _cache[cache_key] = (prof["teams"], time.time())
            return prof["teams"]

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


# =============================================================================
# Поиск игроков
# =============================================================================
def search_liga_source(source_key: str, query: str) -> list[dict]:
    """Парсит поиск игроков по ФИО для LigaStart / Liga5x5."""
    if source_key not in SOURCES:
        return []

    src = SOURCES[source_key]
    cache_key = f"search:{source_key}:{query.strip().lower()}"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return data

    url = f"{src['base_url']}/participants/players?season_id=all&name={quote(query.strip())}"
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
        if h == "#": col["rank"] = i
        elif "Игрок" in h: col["name"] = i
        elif h == "И": col["matches"] = i
        elif h.startswith("Г") and not seen_g:
            col["goals"] = i
            seen_g = True
        elif h == "П": col["assists"] = i
        elif h == "Г+П": col["total_pts"] = i
        elif "ЖК" in h: col["yellow_cards"] = i
        elif "КК" in h: col["red_cards"] = i
        elif "Лм" in h or "MVP" in h: col["mvp"] = i

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
            "teams": []
        })

    _cache[cache_key] = (players, time.time())
    return players


def parse_ffge_player_profile(player_id_or_url) -> dict | None:
    """Парсит официальный профиль игрока на ffge.nagradion.ru/player/{id}."""
    if isinstance(player_id_or_url, int) or str(player_id_or_url).isdigit():
        url = f"https://ffge.nagradion.ru/player/{player_id_or_url}"
    else:
        url = str(player_id_or_url)
        m = re.search(r"/player/(\d+)", url)
        if m:
            url = f"https://ffge.nagradion.ru/player/{m.group(1)}"

    soup = get_soup(url)
    if not soup:
        return None

    html = str(soup)
    m = re.search(r"renderComponent\([^,]+,\s*'PlayerStats',\s*({.*?})\);", html, re.DOTALL)
    if not m:
        return None

    try:
        data = json.loads(m.group(1))
    except Exception:
        return None

    total_matches = 0
    total_goals = 0
    total_assists = 0
    total_yc = 0
    total_rc = 0
    teams_map = {}

    for sport in data.get("sports", []):
        col_map = {}
        for c in sport.get("columns", []):
            label = c.get("label", "").strip().lower()
            key = c.get("key")
            if label in ["игр", "и"]: col_map["played"] = key
            elif label == "м": col_map["protocol"] = key
            elif label in ["г", "голы"]: col_map["goals"] = key
            elif label in ["пас", "п"]: col_map["assists"] = key
            elif label in ["жк", "ж"]: col_map["yc"] = key
            elif label in ["кк", "к"]: col_map["rc"] = key

        for row in sport.get("rows", []):
            st = row.get("stats", {})
            t_obj = row.get("team") or {}
            team_name = t_obj.get("name", "").strip()
            tourn_obj = row.get("tournament") or {}
            tourn_name = tourn_obj.get("name", "").strip()

            matches = 0
            if "played" in col_map and col_map["played"] in st:
                matches = int(st[col_map["played"]])
            elif "protocol" in col_map and col_map["protocol"] in st:
                matches = int(st[col_map["protocol"]])
            elif "matches" in st:
                matches = int(st["matches"])

            goals = int(st[col_map["goals"]]) if "goals" in col_map and col_map["goals"] in st else 0
            assists = int(st[col_map["assists"]]) if "assists" in col_map and col_map["assists"] in st else 0
            yc = int(st[col_map["yc"]]) if "yc" in col_map and col_map["yc"] in st else 0
            rc = int(st[col_map["rc"]]) if "rc" in col_map and col_map["rc"] in st else 0

            if matches == 0 and (goals > 0 or assists > 0):
                matches = max(1, goals)

            total_matches += matches
            total_goals += goals
            total_assists += assists
            total_yc += yc
            total_rc += rc

            if team_name:
                if team_name not in teams_map:
                    teams_map[team_name] = {
                        "team_name": team_name,
                        "matches": 0,
                        "goals": 0,
                        "assists": 0,
                        "yellow_cards": 0,
                        "red_cards": 0,
                        "division": tourn_name
                    }
                t = teams_map[team_name]
                t["matches"] += matches
                t["goals"] += goals
                t["assists"] += assists
                t["yellow_cards"] += yc
                t["red_cards"] += rc

    pname = ""
    if soup.title:
        pname = soup.title.text.replace("- игрок", "").strip()

    return {
        "name": pname,
        "matches": total_matches,
        "goals": total_goals,
        "assists": total_assists,
        "yellow_cards": total_yc,
        "red_cards": total_rc,
        "teams": list(teams_map.values())
    }


def search_ffge_source(query: str) -> list[dict]:
    """Ищет игрока по расширенному пулу турниров на ffge.nagradion.ru с динамическими колонками и профилями."""
    q_low = query.strip().lower()
    if not q_low:
        return []

    cache_key = f"search:ffge:{q_low}"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return data

    tournaments = get_ffge_futsal_tournaments(limit=40)

    def check_tournament(t_info):
        tid, tname = t_info
        url = f"https://ffge.nagradion.ru/tournament{tid}/player-stats"
        soup = get_soup(url)
        if not soup:
            return []

        table = soup.find("table")
        if not table:
            return []

        headers = [th.text.strip().lower() for th in table.select("th")]
        col = {}
        for idx, h in enumerate(headers):
            if any(w in h for w in ["игрок", "участник"]): col["name"] = idx
            elif any(w in h for w in ["команда", "клуб"]): col["team"] = idx
            elif any(w in h for w in ["игр", "игры", "матчи", "и"]): col["matches"] = idx
            elif h in ["г", "голы"]: col["goals"] = idx
            elif any(w in h for w in ["пас", "пасы", "п"]): col["assists"] = idx
            elif "жк" in h: col["yc"] = idx
            elif "кк" in h: col["rc"] = idx

        rows_found = []
        for tr in table.select("tbody tr"):
            tds = [td.text.strip() for td in tr.select("td")]
            if len(tds) < 3:
                continue

            name_idx = col.get("name", 1)
            pname = tds[name_idx] if name_idx < len(tds) else ""
            if q_low in pname.lower():
                a = tr.select_one("a[href*='/player/']")
                p_url = a['href'] if a else ""
                if p_url and not p_url.startswith("http"):
                    p_url = f"https://ffge.nagradion.ru{p_url}"
                m_id = re.search(r"/player/(\d+)", p_url)
                pid = int(m_id.group(1)) if m_id else None

                team_idx = col.get("team", 2)
                team = tds[team_idx] if team_idx < len(tds) else ""
                m_cnt = parse_number(tds[col["matches"]]) if "matches" in col and col["matches"] < len(tds) else 0
                goals = parse_number(tds[col["goals"]]) if "goals" in col and col["goals"] < len(tds) else 0
                assists = parse_number(tds[col["assists"]]) if "assists" in col and col["assists"] < len(tds) else 0
                yc = parse_number(tds[col["yc"]]) if "yc" in col and col["yc"] < len(tds) else 0
                rc = parse_number(tds[col["rc"]]) if "rc" in col and col["rc"] < len(tds) else 0

                if m_cnt == 0 and (goals > 0 or assists > 0):
                    m_cnt = max(1, goals)

                rows_found.append({
                    "pid": pid,
                    "name": pname,
                    "url": p_url,
                    "team": team,
                    "tournament": tname,
                    "matches": m_cnt,
                    "goals": goals,
                    "assists": assists,
                    "yc": yc,
                    "rc": rc
                })
        return rows_found

    with ThreadPoolExecutor(max_workers=10) as ex:
        all_t_rows = list(ex.map(check_tournament, tournaments))

    all_matches = [r for sub in all_t_rows for r in sub]

    grouped_by_pid: dict[int, list] = {}
    for r in all_matches:
        pid = r["pid"]
        if pid:
            if pid not in grouped_by_pid:
                grouped_by_pid[pid] = []
            grouped_by_pid[pid].append(r)

    results = []
    for pid, rows in grouped_by_pid.items():
        prof = parse_ffge_player_profile(pid)
        pname = rows[0]["name"]
        purl = rows[0]["url"]

        if prof and (prof["matches"] > 0 or prof["goals"] > 0 or prof["teams"]):
            results.append({
                "source_id": "ffge",
                "source_name": "ФФГЭ (Наградион)",
                "name": prof["name"] or pname,
                "player_id": pid,
                "player_url": purl or f"https://ffge.nagradion.ru/player/{pid}",
                "matches": prof["matches"],
                "goals": prof["goals"],
                "assists": prof["assists"],
                "total_pts": prof["goals"] + prof["assists"],
                "yellow_cards": prof["yellow_cards"],
                "red_cards": prof["red_cards"],
                "mvp_count": 0,
                "teams": prof["teams"]
            })
        else:
            t_map = {}
            tot_m, tot_g, tot_a, tot_y, tot_r = 0, 0, 0, 0, 0
            for r in rows:
                tot_m += r["matches"]
                tot_g += r["goals"]
                tot_a += r["assists"]
                tot_y += r["yc"]
                tot_r += r["rc"]
                tm = r["team"]
                if tm:
                    if tm not in t_map:
                        t_map[tm] = {
                            "team_name": tm,
                            "matches": 0, "goals": 0, "assists": 0,
                            "yellow_cards": 0, "red_cards": 0,
                            "division": r["tournament"]
                        }
                    t_map[tm]["matches"] += r["matches"]
                    t_map[tm]["goals"] += r["goals"]
                    t_map[tm]["assists"] += r["assists"]
                    t_map[tm]["yellow_cards"] += r["yc"]
                    t_map[tm]["red_cards"] += r["rc"]

            results.append({
                "source_id": "ffge",
                "source_name": "ФФГЭ (Наградион)",
                "name": pname,
                "player_id": pid,
                "player_url": purl or f"https://ffge.nagradion.ru/player/{pid}",
                "matches": tot_m,
                "goals": tot_g,
                "assists": tot_a,
                "total_pts": tot_g + tot_a,
                "yellow_cards": tot_y,
                "red_cards": tot_r,
                "mvp_count": 0,
                "teams": list(t_map.values())
            })

    _cache[cache_key] = (results, time.time())
    return results


def search_all_sources(query: str) -> list[dict]:
    """Ищет игроков по всем 3 сайтам параллельно и группирует по ФИО."""
    q = query.strip()
    if not q or len(q) < 2:
        return []

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_liga5x5 = executor.submit(search_liga_source, "liga5x5", q)
        f_ligastart = executor.submit(search_liga_source, "ligastart", q)
        f_ffge = executor.submit(search_ffge_source, q)

        liga5x5_players = f_liga5x5.result()
        ligastart_players = f_ligastart.result()
        ffge_players = f_ffge.result()

    all_raw = liga5x5_players + ligastart_players + ffge_players

    def enrich_player(p):
        if p["source_id"] in ["liga5x5", "ligastart"] and p.get("player_url"):
            try:
                teams = parse_player_teams_detail(p["player_url"])
                p["teams"] = teams
            except Exception:
                p["teams"] = []
        return p

    with ThreadPoolExecutor(max_workers=8) as executor:
        all_raw = list(executor.map(enrich_player, all_raw))

    grouped: dict[str, dict] = {}

    def get_canonical_key(raw_name: str) -> str:
        tokens = raw_name.strip().split()
        if len(tokens) >= 2:
            return f"{tokens[0].title()} {tokens[1].title()}"
        return raw_name.strip().title()

    for p in all_raw:
        group_key = get_canonical_key(p["name"])
        raw_name = p["name"].strip()

        if group_key not in grouped:
            grouped[group_key] = {
                "name": group_key,
                "full_name": raw_name,
                "accounts": [],
                "all_teams": {},
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

        g = grouped[group_key]
        if len(raw_name.split()) > len(g["full_name"].split()):
            g["full_name"] = raw_name

        src_name = p["source_name"]
        src_id = p["source_id"]

        if src_name not in g["sources_found"]:
            g["sources_found"].append(src_name)

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

        for t in p.get("teams", []):
            tname = t["team_name"]
            if not tname:
                continue
            if tname not in g["all_teams"]:
                g["all_teams"][tname] = {
                    "team_name": tname,
                    "division": t.get("division", src_name),
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

        if src_id not in g["sources_data"]:
            badge_color = SOURCES.get(src_id, {}).get("badge_color", "slate")
            g["sources_data"][src_id] = {
                "source_id": src_id,
                "source_name": src_name,
                "badge_color": badge_color,
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

        g["total_matches"] += p.get("matches", 0)
        g["total_goals"] += p.get("goals", 0)
        g["total_assists"] += p.get("assists", 0)
        g["total_yellow_cards"] += p.get("yellow_cards", 0)
        g["total_red_cards"] += p.get("red_cards", 0)
        g["total_mvp"] += p.get("mvp_count", 0)
        g["total_pts"] += p.get("total_pts", 0)

    result = list(grouped.values())
    for g in result:
        saved_avatar = db.get_avatar(g["name"])
        if saved_avatar:
            g["avatar"] = saved_avatar
    result.sort(key=lambda x: (x["total_goals"] + x["total_assists"]), reverse=True)
    return result


# =============================================================================
# Поиск команд по всем 3 сайтам
# =============================================================================
def search_teams_liga5x5(q: str) -> list[dict]:
    url = f"https://liga5x5.ru/participants/teams?name={quote(q)}"
    soup = get_soup(url)
    if not soup: return []
    links = soup.find_all("a", href=lambda h: h and "/team/" in h)
    found, seen = [], set()
    for a in links:
        href = a['href']
        tname = a.text.strip()
        if tname and href not in seen:
            seen.add(href)
            found.append({
                "source_id": "liga5x5",
                "source_name": "Лига 5х5",
                "team_name": tname,
                "team_url": f"https://liga5x5.ru{href}"
            })
    return found


def search_teams_ligastart(q: str) -> list[dict]:
    url = f"https://ligastart.ru/participants/teams?name={quote(q)}"
    soup = get_soup(url)
    if not soup: return []
    links = soup.find_all("a", href=lambda h: h and "/team/" in h)
    found, seen = [], set()
    for a in links:
        href = a['href']
        tname = a.text.strip()
        if tname and href not in seen:
            seen.add(href)
            found.append({
                "source_id": "ligastart",
                "source_name": "Лига Старт",
                "team_name": tname,
                "team_url": f"https://ligastart.ru{href}"
            })
    return found


def enrich_liga_team_stats(team_info: dict) -> dict:
    url = team_info.get("team_url")
    if not url: return team_info
    soup = get_soup(url)
    if not soup: return team_info
    text = soup.text
    m_games = re.search(r"Игры\s*(\d+)", text, re.IGNORECASE)
    m_wins = re.search(r"Победы\s*(\d+)", text, re.IGNORECASE)
    m_goals = re.search(r"Голы\s*(\d+)", text, re.IGNORECASE)
    m_tourneys = re.search(r"Турниры\s*(\d+)", text, re.IGNORECASE)

    games = int(m_games.group(1)) if m_games else 0
    wins = int(m_wins.group(1)) if m_wins else 0
    goals = int(m_goals.group(1)) if m_goals else 0
    tourneys = int(m_tourneys.group(1)) if m_tourneys else 0

    team_info["games"] = games
    team_info["wins"] = wins
    team_info["goals"] = goals
    team_info["tournaments_count"] = tourneys
    team_info["winrate"] = round(wins / games * 100, 1) if games > 0 else 0
    return team_info


def search_teams_ffge(q: str) -> list[dict]:
    tournaments = get_ffge_futsal_tournaments(limit=35)
    q_low = q.strip().lower()

    def check_t_teams(t_info):
        tid, tname = t_info
        res = []
        try:
            r = req_lib.get(f"https://ffge.nagradion.ru/tournament{tid}/table", headers=HTTP_HEADERS, timeout=6)
            for m in re.finditer(r'renderComponent\("[^"]+",\s*\'TournamentTable\',\s*({.*?})\);', r.text):
                try:
                    data = json.loads(m.group(1))
                    for u in data.get("users", []):
                        raw_name = u.get("name", "")
                        clean_name = re.sub(r'<[^>]+>', '', raw_name).strip()
                        if q_low in clean_name.lower():
                            stats = u.get("stats", {})
                            games = int(stats.get("games", 0)) if str(stats.get("games", 0)).isdigit() else 0
                            wins = int(stats.get("wins", 0)) if str(stats.get("wins", 0)).isdigit() else 0
                            pts = int(stats.get("points", 0)) if str(stats.get("points", 0)).isdigit() else 0
                            diff = stats.get("difference", "0 - 0")
                            m_diff = re.search(r"(\d+)\s*-\s*(\d+)", diff)
                            goals = int(m_diff.group(1)) if m_diff else 0

                            m_link = re.search(r'href="([^"]+)"', raw_name)
                            t_url = m_link.group(1) if m_link else f"https://ffge.nagradion.ru/tournament{tid}"

                            res.append({
                                "source_id": "ffge",
                                "source_name": "ФФГЭ (Наградион)",
                                "team_name": clean_name,
                                "tournament": tname,
                                "tournament_id": tid,
                                "team_url": t_url,
                                "games": games,
                                "wins": wins,
                                "goals": goals,
                                "points": pts,
                                "difference": diff,
                                "tournaments_count": 1,
                                "winrate": round(wins / games * 100, 1) if games > 0 else 0
                            })
                except Exception:
                    pass
        except Exception:
            pass
        return res

    with ThreadPoolExecutor(max_workers=8) as ex:
        all_res = list(ex.map(check_t_teams, tournaments))

    return [t for sub in all_res for t in sub]


def search_all_teams(query: str) -> list[dict]:
    """Ищет команды по всем 3 сайтам, суммирует общую статистику и показывает по турнирам."""
    q = query.strip()
    if not q or len(q) < 2:
        return []

    cache_key = f"teams_search:{q.lower()}"
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return data

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_l5 = ex.submit(search_teams_liga5x5, q)
        f_ls = ex.submit(search_teams_ligastart, q)
        f_ffge = ex.submit(search_teams_ffge, q)

        t_l5 = f_l5.result()
        t_ls = f_ls.result()
        t_ffge = f_ffge.result()

    # Обогащаем команды из лиг 5х5 и старт подробной статистикой
    with ThreadPoolExecutor(max_workers=6) as ex:
        t_l5 = list(ex.map(enrich_liga_team_stats, t_l5))
        t_ls = list(ex.map(enrich_liga_team_stats, t_ls))

    all_teams_raw = t_l5 + t_ls + t_ffge

    # Группируем по каноническому имени команды (например, 'Спортмастер')
    grouped: dict[str, dict] = {}
    for t in all_teams_raw:
        canon_name = t["team_name"].strip()
        canon_key = canon_name.lower()

        if canon_key not in grouped:
            grouped[canon_key] = {
                "team_name": canon_name,
                "sources_found": [],
                "tournaments": [],
                "total_games": 0,
                "total_wins": 0,
                "total_goals": 0,
                "total_tournaments": 0,
                "winrate": 0,
                "sample_url": t.get("team_url")
            }

        g = grouped[canon_key]
        src_name = t["source_name"]
        if src_name not in g["sources_found"]:
            g["sources_found"].append(src_name)

        g["total_games"] += t.get("games", 0)
        g["total_wins"] += t.get("wins", 0)
        g["total_goals"] += t.get("goals", 0)
        g["total_tournaments"] += t.get("tournaments_count", 1)

        # Сохраняем турнир / профиль
        g["tournaments"].append({
            "source_id": t.get("source_id"),
            "source_name": src_name,
            "tournament_name": t.get("tournament", src_name),
            "games": t.get("games", 0),
            "wins": t.get("wins", 0),
            "goals": t.get("goals", 0),
            "points": t.get("points"),
            "difference": t.get("difference"),
            "winrate": t.get("winrate", 0),
            "team_url": t.get("team_url")
        })

    for g in grouped.values():
        if g["total_games"] > 0:
            g["winrate"] = round(g["total_wins"] / g["total_games"] * 100, 1)

    res = list(grouped.values())
    res.sort(key=lambda x: (x["total_games"], x["total_goals"]), reverse=True)
    _cache[cache_key] = (res, time.time())
    return res


# =============================================================================
# FastAPI приложение
# =============================================================================
app = FastAPI(title="Futsal Scout Hub", version="4.0")

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


@app.get("/api/teams/search")
def search_teams_endpoint(q: str = Query(..., min_length=2)):
    results = search_all_teams(q)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }


@app.get("/api/player_teams")
def player_teams_endpoint(url: str = Query(...)):
    teams = parse_player_teams_detail(url)
    return {"url": url, "teams": teams}


@app.post("/api/merge_accounts")
def merge_accounts_endpoint(accounts: list[dict] = Body(...)):
    if len(accounts) < 2:
        raise HTTPException(400, "Для слияния необходимо выбрать как минимум 2 аккаунта!")

    def name_tokens(name_str):
        parts = name_str.strip().lower().split()
        return " ".join(parts[:2]) if len(parts) >= 2 else "".join(parts)

    names = set(name_tokens(a.get("name", "")) for a in accounts)
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

        for t in a.get("teams", []):
            tname = t["team_name"]
            if not tname:
                continue
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


@app.get("/api/favorites")
def get_favorites():
    return db.get_all_favorites()


@app.post("/api/avatar")
def save_avatar_endpoint(data: dict = Body(...)):
    name = data.get("name", "").strip()
    avatar = data.get("avatar", "").strip()
    if not name or not avatar:
        raise HTTPException(400, "Имя и аватар обязательны")
    success = db.save_avatar(name, avatar)
    return {"status": "ok", "saved": success}


@app.get("/api/avatar")
def get_avatar_endpoint(name: str = Query(...)):
    av = db.get_avatar(name)
    return {"name": name, "avatar": av}


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


def scrape_league_table(source_key: str) -> list[dict]:
    """Парсит список игроков для вкладки 'Игроки лиг'."""
    if source_key == "ffge":
        return search_ffge_source(" ")
    return search_liga_source(source_key, "")


@app.get("/api/players")
def get_players_endpoint(source: str = Query("liga5x5"), limit: int = Query(100)):
    players = scrape_league_table(source)
    return {"source": source, "count": len(players[:limit]), "players": players[:limit]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
