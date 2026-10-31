import requests
import json

r = requests.get('https://ffge.nagradion.ru/api/tournament_top_players?tournament=46309&top_by=goals')
print(r.status_code)
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2)[:500])
else:
    print(r.text[:300])
