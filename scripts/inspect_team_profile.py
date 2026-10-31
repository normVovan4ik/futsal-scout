import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ligastart.ru/team/1532688", headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
print("Team page title:", soup.title.text.strip() if soup.title else "")

# check stats block or tables
tables = soup.find_all("table")
print(f"Tables count: {len(tables)}")
for i, t in enumerate(tables):
    headers_row = [th.text.strip() for th in t.select("th")]
    print(f"Table #{i} headers:", headers_row)
    for tr in t.select("tr")[:4]:
        print("  Row:", [td.text.strip().replace("\n", " ") for td in tr.select("td")])

# check other divs with stats
stats_divs = soup.find_all(class_=lambda c: c and any(w in c.lower() for w in ["stat", "info", "block", "record"]))
print(f"Stats divs: {len(stats_divs)}")
for d in stats_divs[:5]:
    text = d.text.strip().replace("\n", " ")
    if any(w in text.lower() for w in ["матч", "побед", "игр", "очк", "гол"]):
        print("  Div:", " ".join(text.split())[:150])
