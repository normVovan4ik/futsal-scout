import requests
from bs4 import BeautifulSoup
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

r = requests.get("https://ligastart.ru/participants/players?season_id=all", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
for a in soup.find_all('a', href=True):
    if '9789962' in a['href'] or '10334610' in a['href']:
        print("LINK text:", a.text.strip(), "href:", a['href'], "parent td:", a.parent.text.strip())
