import sys
import re
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament45832/stats", headers=headers, timeout=10)
# Look for any url or ajax in stats
urls = re.findall(r'https?://[^\s"\'<>]+', r.text)
ffge_urls = set(u for u in urls if "ffge" in u or "nagradion" in u)
for u in sorted(ffge_urls):
    if any(k in u for k in ["stat", "player", "person", "bombardier", "score", "table", "team"]):
        print("Relevant URL:", u)
