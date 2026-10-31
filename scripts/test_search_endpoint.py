import sys
import requests
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

r = requests.get("http://localhost:8000/api/search?q=Ершов", timeout=15)
data = r.json()
print("Query:", data.get("query"))
print("Count:", data.get("count"))
for p in data.get("results", []):
    print(f"\n=== {p['name']} ({p.get('full_name')}) ===")
    print("  Sources:", p.get("sources_found"))
    print("  Accounts count:", len(p.get("accounts", [])))
    for a in p.get("accounts", []):
        t_names = [t['team_name'] for t in a.get('teams', [])]
        print(f"    - [{a['source_name']}] ID: {a['account_id']} | {a['matches']}м, {a['goals']}г | Команды: {t_names}")
    print("  All teams:", list(p.get("all_teams", {}).keys()))
    print(f"  TOTAL: {p['total_matches']} игр, {p['total_goals']} голов, {p['total_assists']} пасов")
