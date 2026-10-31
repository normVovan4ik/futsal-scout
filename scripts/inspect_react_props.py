import sys
import re
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament45832/table", headers=headers, timeout=10)
# search for any data-* attributes in HTML
tags_with_data = re.findall(r'<div[^>]*class="[^"]*react[^"]*"[^>]*>', r.text, re.IGNORECASE)
print("React containers:", tags_with_data)

# search for tournament in html
print("Any 45832 occurrences:", len(re.findall(r'45832', r.text)))
matches = [line for line in r.text.split("\n") if "45832" in line]
for l in matches[:10]:
    print("  Line:", l.strip()[:150])
