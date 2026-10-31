import sys
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/robots.txt", headers=headers, timeout=10)
print("robots.txt:\n", r.text[:1000])

r_s = requests.get("https://ffge.nagradion.ru/sitemap.xml", headers=headers, timeout=10)
print(f"sitemap status: {r_s.status_code}, len: {len(r_s.text)}")
if r_s.status_code == 200:
    print(r_s.text[:1000])
