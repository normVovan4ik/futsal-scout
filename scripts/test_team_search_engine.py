import sys
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 1. Search Liga5x5 Teams
def search_liga5x5_teams(q: str):
    url = f"https://liga5x5.ru/participants/teams?name={requests.utils.quote(q)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "lxml")
        links = soup.find_all("a", href=lambda h: h and "/team/" in h)
        found = []
        seen = set()
        for a in links:
            href = a['href']
            tname = a.text.strip()
            if tname and href not in seen:
                seen.add(href)
                found.append({
                    "source_id": "liga5x5",
                    "source_name": "Лига 5х5",
                    "team_name": tname,
                    "team_url": f"https://liga5x5.ru{href}"
                })
        return found
    except Exception as e:
        print("Liga5x5 team error:", e)
        return []

# 2. Search LigaStart Teams
def search_ligastart_teams(q: str):
    url = f"https://ligastart.ru/participants/teams?name={requests.utils.quote(q)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "lxml")
        links = soup.find_all("a", href=lambda h: h and "/team/" in h)
        found = []
        seen = set()
        for a in links:
            href = a['href']
            tname = a.text.strip()
            if tname and href not in seen:
                seen.add(href)
                found.append({
                    "source_id": "ligastart",
                    "source_name": "Лига Старт",
                    "team_name": tname,
                    "team_url": f"https://ligastart.ru{href}"
                })
        return found
    except Exception as e:
        print("LigaStart team error:", e)
        return []

# Detail stats for a Liga team (Liga5x5 or LigaStart)
def enrich_liga_team_stats(team_info):
    url = team_info["team_url"]
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "lxml")
        # Extract games, wins, draws, losses, goals
        text = soup.text
        # Look for stats pattern like "Игры 29 Победы 17 Голы 147"
        m_games = re.search(r"Игры\s*(\d+)", text, re.IGNORECASE)
        m_wins = re.search(r"Победы\s*(\d+)", text, re.IGNORECASE)
        m_goals = re.search(r"Голы\s*(\d+)", text, re.IGNORECASE)
        m_tourneys = re.search(r"Турниры\s*(\d+)", text, re.IGNORECASE)
        
        team_info["games"] = int(m_games.group(1)) if m_games else 0
        team_info["wins"] = int(m_wins.group(1)) if m_wins else 0
        team_info["goals"] = int(m_goals.group(1)) if m_goals else 0
        team_info["tournaments_count"] = int(m_tourneys.group(1)) if m_tourneys else 0
        
        # Winrate
        team_info["winrate"] = round(team_info["wins"] / team_info["games"] * 100, 1) if team_info["games"] > 0 else 0
    except Exception as e:
        print("Team enrich error:", e)
    return team_info

print("Testing team search for 'Спортмастер'...")
t_ls = search_ligastart_teams("Спортмастер")
print("LigaStart found:", t_ls)
if t_ls:
    enriched = enrich_liga_team_stats(t_ls[0])
    print("Enriched stats:", enriched)

print("\nTesting team search for 'Солянка' in Liga 5x5...")
t_l5 = search_liga5x5_teams("Солянка")
print("Liga 5x5 found:", t_l5)
if t_l5:
    enriched5 = enrich_liga_team_stats(t_l5[0])
    print("Enriched stats 5x5:", enriched5)
