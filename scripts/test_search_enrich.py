import sys
import json
sys.path.insert(0, r'C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout')

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import server

res = server.search_all_sources("Ершов")
print(f"Results: {len(res)}")
if res:
    p = res[0]
    print("Player name:", p["name"])
    print("Accounts count:", len(p["accounts"]))
    for acc in p["accounts"]:
        print(f"  Account ID: {acc['account_id']}, matches: {acc['matches']}, goals: {acc['goals']}")
        print("  Teams:", [t['team_name'] for t in acc['teams']])
    print("All teams summary:", list(p["all_teams"].keys()))
