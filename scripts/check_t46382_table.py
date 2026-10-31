import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46382/table", headers=headers, timeout=10)
# Look for renderComponent
renders = re.findall(r"renderComponent\([\"'][^\"']+[\"'],\s*[\"']([^\"']+)[\"'],\s*({.*?})\);", r.text)
print("Render count:", len(renders))
for cname, cdata in renders:
    print("Component:", cname, "len:", len(cdata))
    if cname == "TournamentTable":
        print("  Snippet:", cdata[:400])
