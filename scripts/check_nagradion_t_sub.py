import requests
from bs4 import BeautifulSoup
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

for sub in ["", "/table", "/bombardiers", "/stats", "/players", "/statistics"]:
    url = f"https://ffge.nagradion.ru/tournament46309{sub}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    print(f"{url} -> status {r.status_code}")
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'lxml')
        tables = soup.find_all('table')
        print(f"  Tables found: {len(tables)}")
        for t in tables[:2]:
            headers = [th.text.strip() for th in t.find_all('th')]
            print("  Table headers:", headers[:8])
            rows = t.find_all('tr')[1:3]
            for row in rows:
                print("   Row:", [td.text.strip() for td in row.find_all('td')][:6])
