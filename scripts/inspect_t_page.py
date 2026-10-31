import requests
from bs4 import BeautifulSoup
import re

r = requests.get("https://ffge.nagradion.ru/tournament46309", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
print("Links on tournament page:")
for a in soup.find_all('a', href=True):
    href = a['href']
    if any(k in href for k in ['team', 'player', 'table', 'stat', 'bombardier', 'scorers']):
        print(f"  {href} -> {a.text.strip()[:40]}")

# Also look for NNData or JSON in scripts
scripts = soup.find_all('script')
for s in scripts:
    text = s.text
    if 'NNData' in text or 'tournament' in text.lower():
        print("Found interesting script:", text[:300])
        break
