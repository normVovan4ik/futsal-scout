import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46309/stats", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Tournament title:", soup.title.text.strip() if soup.title else "")
tables = soup.find_all("table")
print(f"Tables: {len(tables)}")
for i, t in enumerate(tables):
    headers = [th.text.strip() for th in t.select("th")]
    print(f"\n--- Table #{i} (headers: {headers}) ---")
    rows = t.select("tr")
    print(f"Rows count: {len(rows)}")
    for tr in rows[:5]:
        tds = [td.text.strip() for td in tr.select("td")]
        links = [(a.text.strip(), a['href']) for a in tr.select("a[href]")]
        print("  Row:", tds, "Links:", links)
