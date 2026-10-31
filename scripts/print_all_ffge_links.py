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

links = soup.find_all("a", href=True)
print(f"Total links: {len(links)}")
href_samples = set(a["href"] for a in links)
for h in list(href_samples)[:30]:
    print("Link:", h)
