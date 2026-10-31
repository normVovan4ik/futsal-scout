import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Fetch tournament-plan and find the most recent 10 tournament IDs
r = requests.get("https://ffge.nagradion.ru/tournament-plan", headers=headers, timeout=10)
t_ids = re.findall(r"tournament(\d+)", r.text)
unique_tids = list(dict.fromkeys(t_ids))
print("Found tournament IDs:", len(unique_tids))

for tid in unique_tids[:6]:
    for sub in ["", "/stats", "/bombardiers", "/table", "/calendar"]:
        u = f"https://ffge.nagradion.ru/tournament{tid}{sub}"
        try:
            res = requests.get(u, headers=headers, timeout=5)
            # check if page contains any person links or tables
            soup = BeautifulSoup(res.text, "lxml")
            persons = [a['href'] for a in soup.find_all("a", href=True) if "person" in a['href']]
            tables = len(soup.find_all("table"))
            if persons or tables > 0:
                print(f"MATCH: {u} -> tables: {tables}, persons: {len(persons)}")
                if persons:
                    print("  Sample persons:", persons[:3])
        except Exception as e:
            pass
