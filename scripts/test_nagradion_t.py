import requests

headers = {"User-Agent": "Mozilla/5.0"}
# Let's test tournaments
r = requests.get("https://ffge.nagradion.ru/tournament-plan/", headers=headers)
print("Tournament plan status:", r.status_code)
import re
tournaments = re.findall(r'/tournament/(\d+)', r.text)
print("Found tournaments:", set(tournaments[:10]))
if tournaments:
    t_id = tournaments[0]
    for top_by in ["goals", "assists", "goal_pass"]:
        url = f"https://ffge.nagradion.ru/api/tournament_top_players?tournament={t_id}&top_by={top_by}"
        r_top = requests.get(url, headers=headers)
        print(f"Top players {url} -> {r_top.status_code}, len={len(r_top.text)}")
        if r_top.status_code == 200:
            print("SAMPLE:", r_top.text[:300])
