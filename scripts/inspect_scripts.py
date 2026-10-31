import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament45832/table", headers=headers, timeout=10)
print("Len:", len(r.text))
soup = BeautifulSoup(r.text, "lxml")
for script in soup.find_all("script"):
    src = script.get("src")
    if src:
        print("Script src:", src)
    elif script.text and ("window." in script.text or "api" in script.text.lower()):
        print("Script snippet:", script.text[:200])
