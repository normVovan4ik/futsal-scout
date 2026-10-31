import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46382", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Title:", soup.title.text.strip() if soup.title else "")
# All links in tournament
for a in soup.find_all("a", href=True):
    h = a['href']
    if any(k in h for k in ["table", "calendar", "team", "player", "person", "stats"]):
        print("Link:", a.text.strip(), "->", h)
