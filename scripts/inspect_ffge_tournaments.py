import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament-plan", headers=headers, timeout=12)
soup = BeautifulSoup(r.text, "lxml")

print("Title:", soup.title.text.strip() if soup.title else "")
# All tournament links: /tournament/{id} or /tournament/{id}/...
links = soup.find_all("a", href=True)
tournaments = []
for a in links:
    href = a["href"]
    if "/tournament/" in href:
        tournaments.append((a.text.strip(), href))

print(f"Total tournament links: {len(tournaments)}")
# Print first 20 tournaments
for name, href in tournaments[:20]:
    if name:
        print(f"  {name} -> {href}")
