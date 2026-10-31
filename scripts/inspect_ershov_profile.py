import requests
from bs4 import BeautifulSoup
import re
import json

headers = {"User-Agent": "Mozilla/5.0"}
for pid in ["9789962", "10334610"]:
    url = f"https://ligastart.ru/player/{pid}"
    r = requests.get(url, headers=headers, timeout=10)
    print(f"\n=================== PLAYER {pid} ===================")
    soup = BeautifulSoup(r.text, "lxml")
    
    # 1. Title
    print("Title:", soup.title.text if soup.title else "N/A")
    
    # 2. Look for teams
    team_links = soup.find_all("a", href=re.compile(r"/team/"))
    print(f"Team links found: {len(team_links)}")
    for tl in team_links:
        print("  Team:", tl.text.strip(), "href:", tl.get("href"))
        
    # 3. Look for tournaments / divisions
    t_links = soup.find_all("a", href=re.compile(r"/tournament/"))
    print(f"Tournament links found: {len(t_links)}")
    for tl in t_links[:5]:
        print("  Tournament:", tl.text.strip(), "href:", tl.get("href"))

    # 4. Look for all tables
    tables = soup.find_all("table")
    print(f"Tables found: {len(tables)}")
    for i, t in enumerate(tables):
        hdrs = [th.text.strip() for th in t.find_all("th")]
        print(f"  Table {i+1} headers:", hdrs[:8])
        for row in t.find_all("tr")[1:4]:
            print("   Row:", [td.text.strip() for td in row.find_all("td")][:8])
