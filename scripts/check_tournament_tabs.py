import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

t_url = "https://ffge.nagradion.ru/tournament45832"
r = requests.get(t_url, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Tournament 45832 title:", soup.title.text.strip() if soup.title else "")
# check tournament menu / sub-tabs
menu = soup.find_all("a", href=True)
for a in menu:
    if "45832" in a["href"]:
        print("  Sublink:", a.text.strip(), "->", a["href"])
