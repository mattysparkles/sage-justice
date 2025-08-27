import requests
from bs4 import BeautifulSoup

def check_review_visibility(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    snippets = soup.select("div.MjjYud")
    results = [s.get_text(" ", strip=True) for s in snippets[:5]]
    return results
