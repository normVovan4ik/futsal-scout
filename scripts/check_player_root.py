import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

for u in [
    "https://ffge.nagradion.ru/player",
    "https://ffge.nagradion.ru/players",
    "https://ffge.nagradion.ru/player?search=Ершов",
    "https://ffge.nagradion.ru/player/search?q=Ершов",
    "https://ffge.nagradion.ru/players/search?q=Ершов"
]:
    r = requests.get(u, headers=headers, timeout=6)
    print(u, "-> status:", r.status_code, "len:", len(r.text))
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "lxml")
        print("  Title:", soup.title.text.strip() if soup.title else "")
