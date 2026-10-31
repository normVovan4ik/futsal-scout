import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

for site in ["https://liga5x5.ru", "https://ligastart.ru"]:
    url = f"{site}/participants/players"
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    
    # Check forms or filters on participants/players
    forms = soup.find_all("form")
    print(f"=== {site} /participants/players forms: ===")
    for f in forms:
        print("action:", f.get("action"), "inputs:", [(i.get("name"), i.get("type"), i.get("placeholder")) for i in f.find_all("input")])
        print("selects:", [(s.get("name"), [o.get("value") for o in s.find_all("option")][:5]) for s in f.find_all("select")])
    
    # Check pagination
    pagination = soup.find(class_=lambda c: c and "pagin" in c.lower())
    if pagination:
        print("Pagination found:", [a.get("href") for a in pagination.find_all("a")][:5])
    else:
        # Check all links containing page
        page_links = [a.get("href") for a in soup.find_all("a", href=True) if "page=" in a.get("href") or "participants/players" in a.get("href")]
        print("Page links:", page_links[:10])
