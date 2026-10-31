import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament-plan", headers=headers, timeout=12)
soup = BeautifulSoup(r.text, "lxml")

futsal_tournaments = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    m = re.search(r"/tournament(\d+)", href)
    if m:
        tid = m.group(1)
        name = a.text.strip()
        name_l = name.lower()
        if any(w in name_l for w in ["футзал", "мини-футбол", "5х5", "5 на 5"]):
            if not any(t["id"] == tid for t in futsal_tournaments):
                futsal_tournaments.append({"id": tid, "name": name})

print(f"Total futsal tournaments found: {len(futsal_tournaments)}")
for t in futsal_tournaments[:15]:
    print(f"  [{t['id']}] {t['name']}")
