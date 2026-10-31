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
    
    # Extract distinct teams
    teams = {}
    for a in soup.find_all("a", href=True):
        if "/team/" in a["href"]:
            tname = a.text.strip()
            if tname and len(tname) > 1:
                teams[a["href"]] = tname
                
    # Extract tournaments
    tournaments = {}
    for a in soup.find_all("a", href=True):
        if "/tournament/" in a["href"]:
            tname = a.text.strip()
            if tname and len(tname) > 1:
                tournaments[a["href"]] = tname
                
    print(f"\n--- Player {pid} ---")
    print("Teams found:", list(teams.values())[:8])
    print("Tournaments found:", list(tournaments.values())[:5])
    
    # Also check if there's a primary team in header or info block
    # Often in breadcrumbs or under player name
    for el in soup.select(".player-info, .team-name, .current-team, .club, h2, h3"):
        print("  Info block:", el.text.strip()[:60])
