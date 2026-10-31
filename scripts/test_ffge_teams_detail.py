import sys
import re
import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def search_ffge_teams_detail(query: str, max_tournaments=35):
    r = requests.get("https://ffge.nagradion.ru/tournament-plan", headers=headers, timeout=12)
    soup = BeautifulSoup(r.text, "lxml")
    t_list = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"/tournament(\d+)", a["href"])
        if m:
            tid = m.group(1)
            tname = a.text.strip()
            if tname and len(tname) > 3 and not tname.startswith("Шахматка"):
                nl = tname.lower()
                if any(w in nl for w in ["футзал", "мини-футбол", "5х5", "5 на 5", "чемпионат", "первенство", "кубок"]):
                    if not any(t[0] == tid for t in t_list):
                        t_list.append((tid, tname))

    q_low = query.strip().lower()

    def check_t_teams(t_info):
        tid, tname = t_info
        res = []
        try:
            r_table = requests.get(f"https://ffge.nagradion.ru/tournament{tid}/table", headers=headers, timeout=6)
            for m in re.finditer(r'renderComponent\("[^"]+",\s*\'TournamentTable\',\s*({.*?})\);', r_table.text):
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
                                "winrate": round(wins / games * 100, 1) if games > 0 else 0
                            })
                except Exception:
                    pass
        except Exception:
            pass
        return res

    with ThreadPoolExecutor(max_workers=8) as ex:
        all_res = list(ex.map(check_t_teams, t_list[:max_tournaments]))

    return [t for sub in all_res for t in sub]

print("Testing FFGE teams search for 'Спортмастер'...")
res = search_ffge_teams_detail("Спортмастер")
print("Found in FFGE:", res)

print("\nTesting FFGE teams search for 'РИФЕЙ'...")
res2 = search_ffge_teams_detail("РИФЕЙ")
print("Found in FFGE:", res2)
