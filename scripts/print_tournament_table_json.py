import sys
import re
import json
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get("https://ffge.nagradion.ru/tournament46382/table", headers=headers, timeout=10)
renders = re.findall(r"renderComponent\([\"'][^\"']+[\"'],\s*[\"']TournamentTable[\"'],\s*({.*?})\);", r.text)
if renders:
    d = json.loads(renders[0])
    print("Keys in TournamentTable:", d.keys())
    print("Users count:", len(d.get("users", [])))
    if d.get("users"):
        print("Sample user 0:", json.dumps(d["users"][0], indent=2, ensure_ascii=False)[:600])
