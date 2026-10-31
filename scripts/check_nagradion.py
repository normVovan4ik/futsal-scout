import requests
import json
import sys

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
    "Accept": "application/json, text/plain, */*"
}

# Test various Nagradion endpoints
for url in [
    "https://ffge.nagradion.ru/api/players",
    "https://ffge.nagradion.ru/api/search?q=Ершов",
    "https://ffge.nagradion.ru/api/tournaments",
    "https://ffge.nagradion.ru/api/v1/players",
    "https://ffge.nagradion.ru/api",
]:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"{url} -> {r.status_code}, response: {r.text[:200]}")
    except Exception as e:
        print(f"{url} -> err {e}")

# Also check HTML of main nagradion page to see what JS bundle requests
try:
    r = requests.get("https://ffge.nagradion.ru/", headers=headers, timeout=5)
    import re
    scripts = re.findall(r'src="([^"]+\.js)"', r.text)
    print("Nagradion JS scripts:", scripts[:5])
except Exception as e:
    print("Nagradion scripts err:", e)
