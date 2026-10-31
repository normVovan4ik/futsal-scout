import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

u = "https://ffge.nagradion.ru/tournament46382/player-stats"
r = requests.get(u, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
forms = soup.find_all("form")
print(f"Forms on player-stats: {len(forms)}")
for f in forms:
    print("Action:", f.get("action"), "Inputs:", [(i.get("name"), i.get("type")) for i in f.find_all("input")])
    print("Selects:", [(s.get("name"), [o.get("value") for o in s.find_all("option")][:3]) for s in f.find_all("select")])
