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

def parse_number(text: str) -> int:
    m = re.match(r"(\d+)", text.strip())
    return int(m.group(1)) if m else 0

def search_liga_players(base_url, source_id, source_name, query):
    url = f"{base_url}/participants/players?season_id=all&name={requests.utils.quote(query)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if not table:
            return []
        
        headers_row = [th.text.strip() for th in table.select("th")]
        col = {}
        seen_g = False
        for i, h in enumerate(headers_row):
            if h == "#": col["rank"] = i
            elif "Игрок" in h: col["name"] = i
            elif h == "И": col["matches"] = i
            elif h.startswith("Г") and not seen_g:
                col["goals"] = i
                seen_g = True
            elif h == "П": col["assists"] = i
            elif h == "Г+П": col["total_pts"] = i
            elif "ЖК" in h: col["yc"] = i
            elif "КК" in h: col["rc"] = i
            elif "Лм" in h or "MVP" in h: col["mvp"] = i

        players = []
        for tr in table.select("tbody tr"):
            tds = tr.select("td")
            if len(tds) < 3:
                continue
            name_idx = col.get("name", 1)
            if name_idx >= len(tds):
                continue
            name_cell = tds[name_idx]
            name = name_cell.text.strip()
            link = name_cell.select_one("a")
            href = link["href"] if link else ""
            player_url = f"{base_url}{href}" if href else ""
            m_id = re.search(r"/player/(\d+)", href)
            pid = int(m_id.group(1)) if m_id else None

            def val(key):
                idx = col.get(key)
                if idx is not None and idx < len(tds):
                    return parse_number(tds[idx].text)
                return 0

            players.append({
                "source_id": source_id,
                "source_name": source_name,
                "name": name,
                "player_id": pid,
                "player_url": player_url,
                "matches": val("matches"),
                "goals": val("goals"),
                "assists": val("assists"),
                "total_pts": val("total_pts"),
                "yellow_cards": val("yc"),
                "red_cards": val("rc"),
                "mvp_count": val("mvp"),
                "teams": []
            })
        return players
    except Exception as e:
        print(f"Error {source_id}: {e}")
        return []

print("Searching Liga5x5 for 'Ершов'...")
l5 = search_liga_players("https://liga5x5.ru", "liga5x5", "Лига 5х5", "Ершов")
print(f"Liga 5x5: {len(l5)} players found")
for p in l5:
    print(f"  {p['name']} ({p['matches']}и, {p['goals']}г) -> {p['player_url']}")

print("\nSearching LigaStart for 'Ершов'...")
ls = search_liga_players("https://ligastart.ru", "ligastart", "Лига Старт", "Ершов")
print(f"Liga Start: {len(ls)} players found")
for p in ls:
    print(f"  {p['name']} (ID {p['player_id']}, {p['matches']}и, {p['goals']}г) -> {p['player_url']}")
