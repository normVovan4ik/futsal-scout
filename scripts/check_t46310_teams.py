import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46310/player-stats", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
table = soup.find("table")
teams = set()
for tr in table.select("tbody tr"):
    tds = tr.select("td")
    if len(tds) > 2:
        teams.add(tds[2].text.strip())

print("Teams in 46310 (2 Дивизион):", teams)
