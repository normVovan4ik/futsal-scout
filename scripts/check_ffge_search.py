import sys
import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Check nagradion main page or search endpoints
for url in [
    "https://ffge.nagradion.ru/search?q=Ершов",
    "https://ffge.nagradion.ru/search?query=Ершов",
    "https://ffge.nagradion.ru/search?name=Ершов",
    "https://ffge.nagradion.ru/players?search=Ершов",
    "https://ffge.nagradion.ru/tournament-plan",
    "https://nagradion.ru/search?q=Ершов",
    "https://nagradion.ru/search?query=Ершов"
]:
    try:
        r = requests.get(url, headers=headers, timeout=8)
        print(f"URL: {url} -> status {r.status_code}, len {len(r.text)}")
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.text.strip() if soup.title else ""
        print("  Title:", title)
        # Check if any player or person link
        plinks = [a.get("href") for a in soup.find_all("a", href=True) if "person" in a.get("href") or "player" in a.get("href")]
        if plinks:
            print("  Player links:", plinks[:5])
    except Exception as e:
        print(f"URL: {url} -> error {e}")
