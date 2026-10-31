import requests
from bs4 import BeautifulSoup
import re

for pid in ["9789962", "10334610"]:
    url = f"https://ligastart.ru/player/{pid}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    
    # In table of player matches/tournaments
    table = soup.select_one("table")
    print(f"\nPlayer {pid} table rows:")
    if table:
        for tr in table.select("tr")[:10]:
            tds = [td.text.strip() for td in tr.select("td")]
            t_link = tr.select_one("a[href*='/team/']")
            team_name = t_link.text.strip() if t_link else ""
            tour_link = tr.select_one("a[href*='/tournament/']")
            tour_name = tour_link.text.strip() if tour_link else ""
            if tds:
                print("  TDs:", tds[:4], "Team:", team_name, "Tour:", tour_name)
