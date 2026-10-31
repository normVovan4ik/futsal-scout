import sys
import re
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament45832/stats", headers=headers, timeout=10)
print("Stats page status:", r.status_code, "len:", len(r.text))

# Search for renderComponent calls on /stats
renders = re.findall(r"renderComponent\([\"'][^\"']+[\"'],\s*[\"']([^\"']+)[\"'],\s*({.*?})\);", r.text)
print(f"renderComponent calls: {len(renders)}")
for name, data_snippet in renders:
    print("Component:", name, "Data len:", len(data_snippet))
    print("  Snippet:", data_snippet[:250])
