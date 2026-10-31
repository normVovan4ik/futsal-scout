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

main = soup.find("main") or soup.find("div", class_="container") or soup.body
for p in main.find_all(["div", "p", "table", "h1", "h2", "h3", "h4"]):
    t = p.text.strip()
    if any(k in t.lower() for k in ["матч", "гол", "пас", "игр", "статистика", "карточ"]):
        print("MATCH:", t.replace("\n", " ")[:200])
