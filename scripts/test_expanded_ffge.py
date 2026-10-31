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

def get_ffge_tournaments():
    url = "https://ffge.nagradion.ru/tournament-plan"
    r = requests.get(url, headers=headers, timeout=12)
    soup = BeautifulSoup(r.text, "lxml")
    futsal_t = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"/tournament(\d+)", a["href"])
        if m:
            tid = m.group(1)
            name = a.text.strip()
            if name and len(name) > 3 and not name.startswith("Шахматка"):
                nl = name.lower()
                # Филтруем футзал, мини-футбол, 5х5, 6х6, 7х7, Чемпионаты, Кубки и Первенства
                if any(w in nl for w in ["футзал", "мини-футбол", "5х5", "5 на 5", "6х6", "7х7", "чемпионат", "первенство", "кубок", "лига"]):
                    if not any(t[0] == tid for t in futsal_t):
                        futsal_t.append((tid, name))
    return futsal_t

tournaments = get_ffge_tournaments()
print(f"Total tournaments: {len(tournaments)}")

# Возьмем топ-40 самых свежих турниров
recent = tournaments[:40]

def check_tournament_for_player(t_info, query):
    tid, tname = t_info
    url = f"https://ffge.nagradion.ru/tournament{tid}/player-stats"
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if not table:
            return []
        found = []
        for tr in table.select("tbody tr"):
            tds = [td.text.strip() for td in tr.select("td")]
            if len(tds) < 10:
                continue
            pname = tds[1]
            if query.lower() in pname.lower():
                a = tr.select_one("td:nth-of-type(2) a")
                p_url = a['href'] if a else f"https://ffge.nagradion.ru/tournament{tid}"
                team = tds[2] if len(tds) > 2 else ""
                matches = int(re.match(r"(\d+)", tds[3]).group(1)) if len(tds) > 3 and re.match(r"(\d+)", tds[3]) else 0
                goals = int(re.match(r"(\d+)", tds[8]).group(1)) if len(tds) > 8 and re.match(r"(\d+)", tds[8]) else 0
                assists = int(re.match(r"(\d+)", tds[12]).group(1)) if len(tds) > 12 and re.match(r"(\d+)", tds[12]) else 0
                yc = int(re.match(r"(\d+)", tds[14]).group(1)) if len(tds) > 14 and re.match(r"(\d+)", tds[14]) else 0
                rc = int(re.match(r"(\d+)", tds[16]).group(1)) if len(tds) > 16 and re.match(r"(\d+)", tds[16]) else 0
                found.append({
                    "name": pname,
                    "team": team,
                    "tournament": tname,
                    "tid": tid,
                    "matches": matches,
                    "goals": goals,
                    "assists": assists,
                    "yc": yc,
                    "rc": rc,
                    "url": p_url
                })
        return found
    except Exception:
        return []

print("Scanning top-40 FFGE tournaments for 'Ершов' in parallel...")
with ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(lambda t: check_tournament_for_player(t, "Ершов"), recent))

all_found = [p for sub in results for p in sub]
print(f"Total matching records found: {len(all_found)}")
for p in all_found:
    print(f"  {p['name']} | {p['team']} | {p['tournament']} -> {p['matches']}м, {p['goals']}г, {p['assists']}п")
