import requests
from bs4 import BeautifulSoup
import re

for site, url in [
    ("liga5x5", "https://liga5x5.ru/participants/players?season_id=all"),
    ("ligastart", "https://ligastart.ru/participants/players?season_id=all")
]:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(r.text, 'lxml')
    rows = soup.find_all('tr')
    print(f"\n=== {site} (rows: {len(rows)}) ===")
    found = []
    for row in rows:
        text = row.text
        if "Ершов" in text or "ершов" in text.lower():
            cols = [td.text.strip() for td in row.find_all('td')]
            link = row.find('a', href=True)
            href = link['href'] if link else ''
            found.append((cols, href))
    print(f"Found 'Ершов': {len(found)}")
    for f in found[:5]:
        print(" ", f)
