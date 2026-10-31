import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

for u in [
    "https://ffge.nagradion.ru/person495560705",
    "https://nagradion.ru/person495560705",
    "https://ffge.nagradion.ru/person/495560705",
    "https://nagradion.ru/person/495560705",
    "https://ffge.nagradion.ru/player495560705",
]:
    try:
        r = requests.get(u, headers=headers, timeout=8)
        print(f"{u} -> status {r.status_code}, len {len(r.text)}")
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.text.strip() if soup.title else ""
        print("  Title:", title)
    except Exception as e:
        print(f"{u} -> error {e}")
