import sys
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Key adult futsal tournaments
tournaments = [
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
]

def scrape_t_players(t_info):
    tid, tname = t_info
    url = f"https://ffge.nagradion.ru/tournament{tid}/player-stats"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if not table:
            return []
        
        headers_row = [th.text.strip().lower() for th in table.select("th")]
        # find col indices
        col_name = 1
        col_team = 2
        col_matches = 3
        col_goals = 8
        col_assists = 12
        col_yc = 14
        col_rc = 16

        for i, h in enumerate(headers_row):
            if "игрок" in h: col_name = i
            elif "команда" in h: col_team = i
            elif h in ["игр", "и"]: col_matches = i
            elif h in ["г", "голы"]: col_goals = i
            elif "пас" in h or h == "п": col_assists = i
            elif "жк" in h: col_yc = i
            elif "кк" in h: col_rc = i

        res = []
        for tr in table.select("tbody tr"):
            tds = [td.text.strip() for td in tr.select("td")]
            if len(tds) > max(col_name, col_team, col_matches, col_goals):
                pname = tds[col_name]
                p_link = tr.select_one(f"td:nth-of-type({col_name+1}) a")
                p_url = p_link['href'] if p_link else f"https://ffge.nagradion.ru/tournament{tid}"
                
                # numbers
                def to_int(val):
                    m = re.match(r"(\d+)", val)
                    return int(m.group(1)) if m else 0

                matches = to_int(tds[col_matches])
                goals = to_int(tds[col_goals])
                assists = to_int(tds[col_assists]) if col_assists < len(tds) else 0
                yc = to_int(tds[col_yc]) if col_yc < len(tds) else 0
                rc = to_int(tds[col_rc]) if col_rc < len(tds) else 0

                team_name = tds[col_team] if col_team < len(tds) else ""
                
                if pname and len(pname) > 2:
                    res.append({
                        "name": pname,
                        "team": team_name,
                        "tournament": tname,
                        "tournament_id": tid,
                        "player_url": p_url,
                        "matches": matches,
                        "goals": goals,
                        "assists": assists,
                        "yellow_cards": yc,
                        "red_cards": rc
                    })
        return res
    except Exception as e:
        print(f"Error {tid}: {e}")
        return []

with ThreadPoolExecutor(max_workers=5) as ex:
    all_players = list(ex.map(scrape_t_players, tournaments))

flattened = [p for sub in all_players for p in sub]
print(f"Total scraped players from FFGE adult futsal: {len(flattened)}")
# Search for Ershov
ershovs = [p for p in flattened if "ершов" in p["name"].lower()]
print(f"Ershovs found in FFGE: {len(ershovs)}")
for e in ershovs:
    print("  ", e)
