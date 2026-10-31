import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46309/team/443604/players", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

imgs = soup.find_all("img", src=lambda s: s and "person" in s)
if imgs:
    row = imgs[0].find_parent("div", class_="row")
    if row:
        print("Row HTML:")
        print(row.prettify()[:2000])
