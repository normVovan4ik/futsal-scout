import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46309/team/443604/players", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Any person links:", len(soup.find_all("a", href=lambda h: h and "person" in h)))
for a in soup.find_all("a", href=lambda h: h and "person" in h)[:15]:
    print("  Person:", a.text.strip(), a['href'])

# Also check match protocol: /tournament46309/match/4024760
print("\n--- Inspecting Match Protocol 4024760 ---")
r_m = requests.get("https://ffge.nagradion.ru/tournament46309/match/4024760", headers=headers, timeout=10)
soup_m = BeautifulSoup(r_m.text, "lxml")
print("Match title:", soup_m.title.text.strip() if soup_m.title else "")
m_persons = soup_m.find_all("a", href=lambda h: h and "person" in h)
print("Match person links:", len(m_persons))
for a in m_persons[:15]:
    print("  Match person:", a.text.strip(), a['href'])
