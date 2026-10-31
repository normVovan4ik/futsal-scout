import sys
import re
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament45832/table", headers=headers, timeout=10)
matches = re.findall(r"NNData\.queue\.push\((.*?)\);", r.text, re.DOTALL)
print(f"NNData queue pushes: {len(matches)}")
for m in matches:
    print("--- PUSH ---")
    print(m[:300])
