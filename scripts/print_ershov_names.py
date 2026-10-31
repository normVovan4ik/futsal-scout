import requests
from bs4 import BeautifulSoup
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

for p_id in ["9789962", "10334610"]:
    url = f"https://ligastart.ru/player/{p_id}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(r.text, 'lxml')
    title = soup.title.text.strip() if soup.title else ""
    h1 = soup.select_one("h1")
    name = h1.text.strip() if h1 else ""
    print(f"ID {p_id} -> Name: '{name}', Title: '{title}'")
