import sys
import re
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

r = requests.get('https://ffge.nagradion.ru/tournament-plan', headers=headers, timeout=12)
soup = BeautifulSoup(r.text, 'lxml')
futsal_t = []
for a in soup.find_all('a', href=True):
    m = re.search(r'/tournament(\d+)', a['href'])
    if m:
        tid = m.group(1)
        name = a.text.strip()
        if name and len(name) > 3 and not name.startswith('Шахматка'):
            nl = name.lower()
            if any(w in nl for w in ['футзал', 'мини-футбол', '5х5', '5 на 5', 'чемпионат города', 'первенство']):
                if not any(t[0] == tid for t in futsal_t):
                    futsal_t.append((tid, name))

print('Total matching tournaments on FFGE plan:', len(futsal_t))
for tid, name in futsal_t[:30]:
    print(f"[{tid}] {name}")
