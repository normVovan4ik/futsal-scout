import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

print("Forms on home:", len(soup.find_all("form")))
for f in soup.find_all("form"):
    print("  Form:", f.get("action"), f.get("method"), [(i.get("name"), i.get("type")) for i in f.find_all("input")])

# Search for any inputs on home page
inputs = soup.find_all("input")
print(f"Inputs on home: {len(inputs)}")
for inp in inputs:
    print("  Input:", inp.get("name"), inp.get("type"), inp.get("placeholder"))

# Search for any 'search' in JS or links
search_links = [a.get("href") for a in soup.find_all("a", href=True) if "search" in a.get("href") or "find" in a.get("href")]
print("Search links:", search_links)
