import requests
import json

headers = {"User-Agent": "Mozilla/5.0"}
for ep in [
    "https://ffge.nagradion.ru/api/people?lastName=Ершов",
    "https://ffge.nagradion.ru/api/people?name=Ершов",
    "https://ffge.nagradion.ru/api/people?search=Ершов",
    "https://ffge.nagradion.ru/api/tournament_top_players",
    "https://ffge.nagradion.ru/api/players/statistics?player=1",
]:
    try:
        r = requests.get(ep, headers=headers, timeout=5)
        print(f"{ep} -> {r.status_code}")
        if r.status_code == 200:
            print("  DATA:", r.text[:300])
        else:
            print("  ERR:", r.text[:200])
    except Exception as e:
        print(f"{ep} -> {e}")
