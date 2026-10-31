import sys
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 1. Test Player Search across 3 leagues
print("--- 1. Testing Player Search (/api/search?q=Ершов) ---")
r1 = requests.get("http://localhost:8000/api/search?q=Ершов", timeout=20)
d1 = r1.json()
print("Total players found:", d1.get("count"))
for p in d1.get("results", [])[:3]:
    print(f"  {p['name']} ({p['full_name']}) | Источники: {p['sources_found']} | Аккаунтов: {len(p['accounts'])} | Голов: {p['total_goals']}")

# 2. Test Team Search across 3 leagues
print("\n--- 2. Testing Team Search (/api/teams/search?q=Спортмастер) ---")
r2 = requests.get("http://localhost:8000/api/teams/search?q=Спортмастер", timeout=20)
d2 = r2.json()
print("Total teams found:", d2.get("count"))
for t in d2.get("results", []):
    print(f"  Команда: {t['team_name']} | Лиги: {t['sources_found']} | Всего игр: {t['total_games']} | Побед: {t['total_wins']} | Голов: {t['total_goals']} | Винрейт: {t['winrate']}%")
    print(f"  Турниров/дивизионов: {len(t['tournaments'])}")

print("\n--- 3. Testing Team Search for 'Рифей' ---")
r3 = requests.get("http://localhost:8000/api/teams/search?q=Рифей", timeout=20)
d3 = r3.json()
print("Total teams found:", d3.get("count"))
for t in d3.get("results", []):
    print(f"  Команда: {t['team_name']} | Лиги: {t['sources_found']} | Всего игр: {t['total_games']} | Побед: {t['total_wins']} | Голов: {t['total_goals']} | Винрейт: {t['winrate']}%")

print("\n--- 4. Testing Favorites DB with custom avatar ---")
fav_test = {
    "name": "Ершов Владимир",
    "position": "PIV",
    "team": "Спортмастер",
    "avatar": "data:image/svg+xml;utf8,<svg></svg>",
    "matches": 107,
    "team_matches": 107,
    "goals": 123,
    "assists": 39,
    "yellow_cards": 8,
    "red_cards": 0,
    "mvp_count": 1,
    "notes": "Основной голеадор, проверено сохранение своего фото"
}
r4 = requests.post("http://localhost:8000/api/favorites", json=fav_test, timeout=5)
print("Save favorite status:", r4.json())
favs = requests.get("http://localhost:8000/api/favorites", timeout=5).json()
print("Favorites in DB:", len(favs), "First fav avatar exists:", bool(favs[0].get("avatar")))
