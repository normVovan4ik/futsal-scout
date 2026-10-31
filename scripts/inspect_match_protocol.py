import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46382/match/4002743", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
print("Match title:", soup.title.text.strip() if soup.title else "")

# Check tables or goalscorers
for t in soup.find_all("table"):
    th = [h.text.strip() for h in t.select("th")]
    print("Table th:", th)
    for tr in t.select("tr")[:4]:
        print("  Row:", [td.text.strip().replace("\n", " ") for td in tr.select("td")])

# Check all links
links = [(a.text.strip(), a['href']) for a in soup.find_all("a", href=True) if any(k in a['href'] for k in ["player", "person", "team"])]
print("Player/team links in match:", len(links))
for text, href in links[:15]:
    print("  Link:", text, "->", href)
