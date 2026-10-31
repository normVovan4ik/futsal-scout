import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

u = "https://ffge.nagradion.ru/tournament46309/player/271429"
r = requests.get(u, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Title:", soup.title.text.strip() if soup.title else "")
tables = soup.find_all("table")
print("Tables count:", len(tables))
for i, t in enumerate(tables):
    headers = [th.text.strip() for th in t.select("th")]
    print(f"Table #{i} headers:", headers)
    for tr in t.select("tr")[:5]:
        tds = [td.text.strip() for td in tr.select("td")]
        if tds:
            print("  Row:", tds)
