import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

for site in ["https://liga5x5.ru", "https://ligastart.ru"]:
    url = f"{site}/participants/players?season_id=all&name=Ершов"
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    rows = soup.select("table tbody tr")
    print(f"=== {site} search 'Ершов': {len(rows)} rows found ===")
    for tr in rows[:5]:
        tds = [td.text.strip() for td in tr.select("td")]
        a = tr.select_one("a[href*='/player/']")
        href = a['href'] if a else None
        print("  Player:", a.text.strip() if a else "No link", href, "Tds:", tds)
