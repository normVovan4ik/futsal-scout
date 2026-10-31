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
    u0 = d["users"][0]
    print("User 0 name:", u0.get("name"))
    print("User 0 stats:", u0.get("stats"))
    print("Keys info:", d.get("keys_info"))
