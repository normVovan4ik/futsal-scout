import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 1. Liga 5x5 teams: /participants/teams
r1 = requests.get("https://liga5x5.ru/participants/teams?season_id=all", headers=headers, timeout=10)
s1 = BeautifulSoup(r1.text, "lxml")
forms1 = s1.find_all("form")
print("Liga5x5 /participants/teams forms:", len(forms1))
for f in forms1:
    print("  Inputs:", [(i.get("name"), i.get("type"), i.get("placeholder")) for i in f.find_all("input")])
table1 = s1.find("table")
if table1:
    print("Liga5x5 teams table headers:", [th.text.strip() for th in table1.select("th")])
    for tr in table1.select("tbody tr")[:3]:
        print("  Row:", [td.text.strip() for td in tr.select("td")])

# 2. Liga Start teams: /participants/teams
r2 = requests.get("https://ligastart.ru/participants/teams?season_id=all", headers=headers, timeout=10)
s2 = BeautifulSoup(r2.text, "lxml")
forms2 = s2.find_all("form")
print("\nLigaStart /participants/teams forms:", len(forms2))
for f in forms2:
    print("  Inputs:", [(i.get("name"), i.get("type"), i.get("placeholder")) for i in f.find_all("input")])
table2 = s2.find("table")
if table2:
    print("LigaStart teams table headers:", [th.text.strip() for th in table2.select("th")])
    for tr in table2.select("tbody tr")[:3]:
        print("  Row:", [td.text.strip() for td in tr.select("td")])
