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

def search_ffge_teams(q: str):
    # Search team across recent adult tournaments on ffge
    # On ffge, /tournament{tid}/table has users list with team names and links!
    # Let's inspect how many tournaments have this team:
    tids = [
        ("46382", "Финал Чемпионата Екатеринбурга 5х5 (2026)"),
        ("46309", "Чемпионат города 1 Дивизион (26/27)"),
        ("46310", "Чемпионат города 2 Дивизион (26/27)"),
        ("46315", "Чемпионат города 3 Дивизион (26/27)"),
        ("46316", "Чемпионат города 4 Дивизион (26/27)"),
        ("45832", "Первенство Чкаловского района 5х5 (2026)"),
        ("45862", "Первенство Кировского района 5х5 (2026)"),
        ("45884", "Первенство Железнодорожного района 5х5 (2026)"),
        ("45993", "Первенство Академического района 5х5 (2026)"),
    ]
    q_low = q.strip().lower()
    found = []
    for tid, tname in tids:
        u = f"https://ffge.nagradion.ru/tournament{tid}/table"
        try:
            r = requests.get(u, headers=headers, timeout=6)
            for m in re.finditer(r'<a href="([^"]*tournament\d+/team/\d+/players)">([^<]+)</a>', r.text):
                t_url, t_name = m.group(1), m.group(2).strip()
                if q_low in t_name.lower():
                    found.append({"source_id": "ffge", "source_name": "ФФГЭ (Наградион)", "team_name": t_name, "tournament": tname, "url": t_url})
        except Exception:
            pass
    return found

print("Searching FFGE teams for 'Спортмастер'...")
res = search_ffge_teams("Спортмастер")
print("Found in FFGE:", res)
