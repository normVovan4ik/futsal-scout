import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

for site in ["https://liga5x5.ru", "https://ligastart.ru"]:
    u = f"{site}/participants/teams?season_id=all&name=Спортмастер"
    r = requests.get(u, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table")
    print(f"=== {site} team search 'Спортмастер' ===")
    if table:
        print("Headers:", [th.text.strip() for th in table.select("th")])
        for tr in table.select("tbody tr")[:5]:
            tds = [td.text.strip() for td in tr.select("td")]
            a = tr.select_one("a[href*='/team/']")
            print("  Team row:", tds, "Link:", a['href'] if a else None)
    else:
        print("No table found")
