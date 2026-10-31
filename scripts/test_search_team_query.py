import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ligastart.ru/participants/teams?name=Спортмастер", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
links = soup.find_all("a", href=lambda h: h and "/team/" in h)
print("Searched 'Спортмастер' team links count:", len(links))
for a in links:
    print("Team:", a.text.strip(), a['href'])
