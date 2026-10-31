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

tournaments = []
# On tournament-plan, find all tournament blocks or links
for a in soup.find_all("a", href=True):
    href = a["href"]
    m = re.search(r"/tournament(\d+)", href)
    if m:
        tid = m.group(1)
        name = a.text.strip()
        if name and len(name) > 3 and not name.startswith("Шахматка"):
            parent_tr = a.find_parent("tr")
            date_info = parent_tr.text.strip().replace("\n", " ") if parent_tr else ""
            tournaments.append({
                "id": tid,
                "name": name,
                "date": date_info[:100]
            })

# Deduplicate by id
unique = {}
for t in tournaments:
    if t["id"] not in unique:
        unique[t["id"]] = t

print(f"Unique tournaments on plan: {len(unique)}")
# Print first 25 (most recent)
for t in list(unique.values())[:25]:
    print(f"[{t['id']}] {t['name']}")
