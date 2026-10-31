import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46309/team/443604/players", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")

imgs = soup.find_all("img", src=lambda s: s and "person" in s)
print(f"Person images: {len(imgs)}")
for img in imgs:
    parent = img.find_parent("li") or img.find_parent("tr") or img.find_parent("div", class_=lambda c: c and ("player" in c.lower() or "person" in c.lower() or "item" in c.lower())) or img.parent
    print("Img parent text:", parent.text.strip().replace("\n", " ") if parent else "No parent")
    # check links inside parent
    links = [(a.text.strip(), a['href']) for a in parent.find_all("a", href=True)]
    print("  Links:", links)
