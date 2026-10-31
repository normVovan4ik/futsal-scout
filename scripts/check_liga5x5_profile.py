import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get('https://liga5x5.ru/player/6005087', headers=headers, timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
print("Profile title:", soup.title.text.strip() if soup.title else "")
for tr in soup.select('table tr'):
    tds = [td.text.strip() for td in tr.select('td')]
    links = [(a.text.strip(), a['href']) for a in tr.select('a[href]')]
    if tds or links:
        print("Row:", tds, "Links:", links)
