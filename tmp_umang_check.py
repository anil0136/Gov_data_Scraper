import requests
from bs4 import BeautifulSoup
url='https://web.umang.gov.in/landing/scheme/category/Agriculture,Rural%20&%20Environment'
try:
    r = requests.get(url, timeout=20)
    print('status', r.status_code)
    text = r.text
    print(text[:1200])
    soup = BeautifulSoup(text, 'html.parser')
    cards = soup.find_all('mat-card')
    print('mat-card count', len(cards))
    if cards:
        print(cards[0])
    else:
        out = []
        for tag in soup.find_all(True)[:40]:
            out.append(f'{tag.name} {tag.attrs}')
        print('\n'.join(out))
except Exception as e:
    print('ERROR:', type(e).__name__, e)
