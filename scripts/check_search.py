import requests
import json
import re
from bs4 import BeautifulSoup
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124"
}

# 1. Nagradion check
print("--- 1. Nagradion search check ---")
for url in ["https://ffge.nagradion.ru/search?q=Ершов", "https://ffge.nagradion.ru/players?search=Ершов", "https://ffge.nagradion.ru/api/players?query=Ершов"]:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"{url} -> status {r.status_code}")
    except Exception as e:
        print(f"{url} -> err {e}")

# 2. Check liga5x5 / ligastart search or player parsing
print("\n--- 2. Liga5x5 / LigaStart search check ---")
for base in ["https://liga5x5.ru", "https://ligastart.ru"]:
    try:
        r = requests.get(f"{base}/participants/players?season_id=all", headers=headers, timeout=10)
        print(f"{base} /participants/players?season_id=all -> status {r.status_code}, len={len(r.text)}")
    except Exception as e:
        print(f"{base} -> err {e}")
