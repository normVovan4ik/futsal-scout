import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://nagradion.ru/search?q=Ершов", headers=headers, timeout=12)
soup = BeautifulSoup(r.text, "lxml")

# Look for result sections (Люди / Игроки / Турниры / Команды)
print("=== Headings / Sections on nagradion search ===")
for h in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
    print("Heading:", h.text.strip())

# Check links with /person/ or /player/
people = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/person/" in href or "/player/" in href:
        text = a.text.strip()
        if text and len(text) > 2 and text not in [p['name'] for p in people]:
            # find parent container info
            parent = a.find_parent("li") or a.find_parent("tr") or a.find_parent("div")
            extra = parent.text.replace(text, "").strip() if parent else ""
            people.append({"name": text, "href": href, "extra": " ".join(extra.split())[:100]})

print(f"=== Found {len(people)} people links: ===")
for p in people[:15]:
    print("Person:", p["name"], "| URL:", p["href"], "| Extra:", p["extra"])
