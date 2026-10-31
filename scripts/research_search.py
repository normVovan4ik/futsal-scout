import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

sites = [
    ("liga5x5", "https://liga5x5.ru"),
    ("ligastart", "https://ligastart.ru"),
    ("ffge", "https://ffge.nagradion.ru")
]

for name, base in sites:
    print(f"=== {name}: {base} ===")
    try:
        r = requests.get(base, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        forms = soup.find_all("form")
        for f in forms:
            print("Form action:", f.get("action"), "method:", f.get("method"))
            for inp in f.find_all(["input", "button"]):
                print("  elem:", inp.name, inp.get("name"), inp.get("type"), inp.get("placeholder"))
        
        # Check all links containing search, player, tournament
        links = [a.get("href") for a in soup.find_all("a", href=True) if any(w in a.get("href") for w in ["search", "player", "participant", "people"])]
        print("Relevant links:", links[:10])
    except Exception as e:
        print("Error:", e)
