import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46309/calendar", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Calendar title:", soup.title.text.strip() if soup.title else "")
# Check match links
matches = [a['href'] for a in soup.find_all("a", href=True) if "/match/" in a['href'] or "/game/" in a['href'] or "match" in a['href']]
print("Match links count:", len(matches))
for m in matches[:10]:
    print("  Match link:", m)

# Also check any team links or person links
teams = [a['href'] for a in soup.find_all("a", href=True) if "team" in a['href'] or "club" in a['href']]
print("Team links count:", len(teams))
for t in teams[:10]:
    print("  Team link:", t)
