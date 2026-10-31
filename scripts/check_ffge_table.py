import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

t_url = "https://ffge.nagradion.ru/tournament45832/table"
r = requests.get(t_url, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Tables count:", len(soup.find_all("table")))
for i, table in enumerate(soup.find_all("table")):
    headers = [th.text.strip() for th in table.select("th")]
    print(f"Table #{i} headers:", headers)
    # Check if there are player links or team links
    plinks = [a['href'] for a in table.select("a[href*='person'], a[href*='player'], a[href*='team']")]
    print(f"  Sample links in table #{i}:", plinks[:5])
