import requests
from bs4 import BeautifulSoup

r = requests.get('https://ffge.nagradion.ru/tournament-plan', timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
print("Title:", soup.title.text if soup.title else "N/A")
for a in soup.find_all('a', href=True):
    print("Link:", a['href'], "Text:", a.text.strip())
