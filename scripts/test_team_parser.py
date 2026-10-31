import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

def parse_player_teams_and_divisions(player_url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(player_url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    
    table = soup.select_one("table")
    if not table:
        return []
        
    teams_stats = {}
    
    current_team = None
    current_tour = None
    
    for tr in table.select("tr"):
        tds = [td.text.strip() for td in tr.select("td")]
        # Check if this row is a team summary row:
        # Format: ['', 'Matches', 'Goals', 'Assists', 'YC', 'RC'] or ['TeamName', 'Matches', 'Goals', ...]
        if len(tds) >= 4:
            # Check if tds[0] or tds[1] has team name
            t_link = tr.select_one("a[href*='/team/']")
            team_name = t_link.text.strip() if t_link else (tds[0] if len(tds[0]) > 2 and not any(c.isdigit() for c in tds[0]) else "")
            
            # Check for tournament header
            tour_link = tr.select_one("a[href*='/tournament/']")
            tour_name = tour_link.text.strip() if tour_link else ""
            
            # Sub-team total row usually has: tds[0]=TeamName, tds[1]=Matches (digits), tds[2]=Goals (digits)
            if team_name and re.match(r"^\d+$", tds[1]) and re.match(r"^\d+", tds[2]):
                matches = int(tds[1])
                goals = int(re.match(r"^(\d+)", tds[2]).group(1))
                assists = int(tds[3]) if len(tds) > 3 and tds[3].isdigit() else 0
                yc = int(tds[4]) if len(tds) > 4 and tds[4].isdigit() else 0
                rc = int(tds[5]) if len(tds) > 5 and tds[5].isdigit() else 0
                
                key = team_name
                if key not in teams_stats:
                    teams_stats[key] = {
                        "team_name": team_name,
                        "tournaments": [],
                        "matches": 0,
                        "goals": 0,
                        "assists": 0,
                        "yellow_cards": 0,
                        "red_cards": 0
                    }
                teams_stats[key]["matches"] += matches
                teams_stats[key]["goals"] += goals
                teams_stats[key]["assists"] += assists
                teams_stats[key]["yellow_cards"] += yc
                teams_stats[key]["red_cards"] += rc

    return list(teams_stats.values())

for pid in ["9789962", "10334610"]:
    res = parse_player_teams_and_divisions(f"https://ligastart.ru/player/{pid}")
    print(f"\nTeams for {pid}:")
    for t in res:
        print(" ", t)
