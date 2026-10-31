import requests
import re

r = requests.get('https://ffge.nagradion.ru/sitemap/sitemap.xml', timeout=10)
print('Sitemap status:', r.status_code)
if r.status_code == 200:
    urls = re.findall(r'<loc>([^<]+)</loc>', r.text)
    print(f'Total URLs in sitemap: {len(urls)}')
    player_urls = [u for u in urls if '/player/' in u]
    tournament_urls = [u for u in urls if '/tournament/' in u]
    print(f'Player URLs: {len(player_urls)}, examples: {player_urls[:5]}')
    print(f'Tournament URLs: {len(tournament_urls)}, examples: {tournament_urls[:5]}')
