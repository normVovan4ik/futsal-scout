import requests
import re
from bs4 import BeautifulSoup

r = requests.get('https://ffge.nagradion.ru/', timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
links = [a['href'] for a in soup.find_all('a', href=True)]
print("All links on ffge.nagradion.ru:")
for l in sorted(set(links)):
    print(" ", l)
