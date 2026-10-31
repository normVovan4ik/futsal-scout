import requests
import json

r = requests.get('https://ffge.nagradion.ru/api', timeout=10)
data = r.json()
print("Nagradion Endpoints:")
for k, v in data.items():
    print(f"  {k}: {v}")
