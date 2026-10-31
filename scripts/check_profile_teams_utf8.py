import requests
from bs4 import BeautifulSoup
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

for pid in ["9789962", "10334610"]:
    url = f"https://ligastart.ru/player/{pid}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    
    table = soup.select_one("table")
    print(f"\n================ Player {pid} ================")
    if table:
        for tr in table.select("tr"):
            tds = [td.text.strip() for td in tr.select("td")]
            t_link = tr.select_one("a[href*='/team/']")
            team_name = t_link.text.strip() if t_link else ""
            tour_link = tr.select_one("a[href*='/tournament/']")
            tour_name = tour_link.text.strip() if tour_link else ""
            # If the row has tournament or team header
            if len(tds) >= 4 and team_name:
                print(f"  Team: '{team_name}' | Tour: '{tour_name}' | TDs: {tds}")
