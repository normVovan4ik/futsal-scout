import sys
import re
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def parse_number(text: str) -> int:
    m = re.match(r"(\d+)", text.strip())
    return int(m.group(1)) if m else 0

# 1. Search Liga5x5
def search_liga5x5(query: str) -> list[dict]:
    url = f"https://liga5x5.ru/participants/players?season_id=all&name={requests.utils.quote(query)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if not table: return []
        players = []
        for tr in table.select("tbody tr"):
            tds = tr.select("td")
            if len(tds) < 3: continue
            a = tr.select_one("a[href*='/player/']")
            if not a: continue
            name = a.text.strip()
            href = a['href']
            m_id = re.search(r"/player/(\d+)", href)
            pid = int(m_id.group(1)) if m_id else None
            p_url = f"https://liga5x5.ru{href}"
            matches = parse_number(tds[2].text) if len(tds) > 2 else 0
            goals = parse_number(tds[3].text) if len(tds) > 3 else 0
            assists = parse_number(tds[5].text) if len(tds) > 5 else 0
            yc = parse_number(tds[8].text) if len(tds) > 8 else 0
            rc = parse_number(tds[9].text) if len(tds) > 9 else 0
            mvp = parse_number(tds[10].text) if len(tds) > 10 else 0
            players.append({
                "source_id": "liga5x5",
                "source_name": "Лига 5х5",
                "name": name,
                "player_id": pid,
                "player_url": p_url,
                "matches": matches,
                "goals": goals,
                "assists": assists,
                "total_pts": goals + assists,
                "yellow_cards": yc,
                "red_cards": rc,
                "mvp_count": mvp,
                "teams": []
            })
        return players
    except Exception as e:
        print(f"Error liga5x5: {e}")
        return []

# 2. Search LigaStart
def search_ligastart(query: str) -> list[dict]:
    url = f"https://ligastart.ru/participants/players?season_id=all&name={requests.utils.quote(query)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if not table: return []
        players = []
        for tr in table.select("tbody tr"):
            tds = tr.select("td")
            if len(tds) < 3: continue
            a = tr.select_one("a[href*='/player/']")
            if not a: continue
            name = a.text.strip()
            href = a['href']
            m_id = re.search(r"/player/(\d+)", href)
            pid = int(m_id.group(1)) if m_id else None
            p_url = f"https://ligastart.ru{href}"
            matches = parse_number(tds[2].text) if len(tds) > 2 else 0
            goals = parse_number(tds[3].text) if len(tds) > 3 else 0
            assists = parse_number(tds[5].text) if len(tds) > 5 else 0
            yc = parse_number(tds[8].text) if len(tds) > 8 else 0
            rc = parse_number(tds[9].text) if len(tds) > 9 else 0
            mvp = parse_number(tds[10].text) if len(tds) > 10 else 0
            players.append({
                "source_id": "ligastart",
                "source_name": "Лига Старт",
                "name": name,
                "player_id": pid,
                "player_url": p_url,
                "matches": matches,
                "goals": goals,
                "assists": assists,
                "total_pts": goals + assists,
                "yellow_cards": yc,
                "red_cards": rc,
                "mvp_count": mvp,
                "teams": []
            })
        return players
    except Exception as e:
        print(f"Error ligastart: {e}")
        return []

# 3. Search FFGE Nagradion
FFGE_TOURNAMENTS = [
    ("46382", "Финал Чемпионата Екатеринбурга 5х5 (2026)"),
    ("46309", "Чемпионат города 1 Дивизион (26/27)"),
    ("46310", "Чемпионат города 2 Дивизион (26/27)"),
    ("46315", "Чемпионат города 3 Дивизион (26/27)"),
    ("46316", "Чемпионат города 4 Дивизион (26/27)"),
    ("45832", "Первенство Чкаловского района 5х5 (2026)"),
    ("45862", "Первенство Кировского района 5х5 (2026)"),
    ("45884", "Первенство Железнодорожного района 5х5 (2026)"),
    ("45993", "Первенство Академического района 5х5 (2026)"),
    ("45914", "Турнир по мини-футболу 5х5 лето 2026"),
    ("46051", "Кубок Лиги заводов 6х6 (2026)"),
    ("45449", "Кубок ФФГЕ 5х5"),
    ("46327", "Турнир памяти Самойлова 5х5")
]

def search_ffge(query: str) -> list[dict]:
    q_low = query.strip().lower()
    def check_t(t_info):
        tid, tname = t_info
        url = f"https://ffge.nagradion.ru/tournament{tid}/player-stats"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code != 200: return []
            soup = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if not table: return []
            found = []
            for tr in table.select("tbody tr"):
                tds = [td.text.strip() for td in tr.select("td")]
                if len(tds) < 10: continue
                pname = tds[1]
                if q_low in pname.lower():
                    a = tr.select_one("td:nth-of-type(2) a")
                    p_url = a['href'] if a else f"https://ffge.nagradion.ru/tournament{tid}"
                    m_id = re.search(r"/player/(\d+)", p_url)
                    pid = int(m_id.group(1)) if m_id else None
                    team = tds[2] if len(tds) > 2 else ""
                    m_cnt = parse_number(tds[3]) if len(tds) > 3 else 0
                    goals = parse_number(tds[8]) if len(tds) > 8 else 0
                    assists = parse_number(tds[12]) if len(tds) > 12 else 0
                    yc = parse_number(tds[14]) if len(tds) > 14 else 0
                    rc = parse_number(tds[16]) if len(tds) > 16 else 0
                    found.append({
                        "source_id": "ffge",
                        "source_name": "ФФГЭ (Наградион)",
                        "name": pname,
                        "player_id": pid,
                        "player_url": p_url,
                        "matches": m_cnt,
                        "goals": goals,
                        "assists": assists,
                        "total_pts": goals + assists,
                        "yellow_cards": yc,
                        "red_cards": rc,
                        "mvp_count": 0,
                        "teams": [{"team_name": team, "matches": m_cnt, "goals": goals, "assists": assists, "yellow_cards": yc, "red_cards": rc, "division": tname}] if team else []
                    })
            return found
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(check_t, FFGE_TOURNAMENTS))
    return [p for sub in results for p in sub]

t0 = time.time()
with ThreadPoolExecutor(max_workers=3) as ex:
    f1 = ex.submit(search_liga5x5, "Ершов")
    f2 = ex.submit(search_ligastart, "Ершов")
    f3 = ex.submit(search_ffge, "Ершов")
    r1, r2, r3 = f1.result(), f2.result(), f3.result()

print(f"Done in {time.time()-t0:.2f}s:")
print(f"  Liga 5x5: {len(r1)} players")
print(f"  Liga Start: {len(r2)} players")
print(f"  FFGE: {len(r3)} players")

all_found = r1 + r2 + r3
print(f"Total across all 3: {len(all_found)} records")
for p in all_found:
    print(f"[{p['source_name']}] {p['name']} (ID {p['player_id']}) -> {p['matches']}м, {p['goals']}г, {p['assists']}п | Команды: {[t['team_name'] for t in p['teams']]}")
