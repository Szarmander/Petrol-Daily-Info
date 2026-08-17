import os
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

FILE_STATUS = "status.txt"
last_title = ""

if os.path.exists(FILE_STATUS):
    with open(FILE_STATUS, "r", encoding="utf-8") as f:
        last_title = f.read().strip()

BASE_URL = "https://www.gov.pl"
NEWS_URL = f"{BASE_URL}/web/energia/wiadomosci"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

session = requests.Session()
retry = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[403, 429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update(headers)

print("Searching for the latest fuel prices article...")

try:
    response = session.get(NEWS_URL, timeout=15)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"❌ Nie udało się połączyć ze stroną gov.pl. Błąd: {e}")
    sys.exit(1)

soup = BeautifulSoup(response.content, "html.parser")

link_for_article = None
found_title = None

for a in soup.find_all("a", href=True):
    title = a.get_text(strip=True)
    if "maksymalna cena detaliczna paliw" in title.lower():
        link_for_article = a.get("href")
        found_title = title
        break

if not link_for_article:
    print("Article not found")
    sys.exit(0)

print(f"Found article: '{found_title}'")

if found_title == last_title:
    print("Already checked the latest article. Exiting.")
    sys.exit(0)

if not link_for_article.startswith("http"):
    link_for_article = BASE_URL + link_for_article

try:
    art_response = session.get(link_for_article, timeout=15)
    art_response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"❌ Nie udało się wejść w artykuł. Błąd: {e}")
    sys.exit(1)

art_soup = BeautifulSoup(art_response.content, "html.parser")

prices = []

info_container = art_soup.find("div", class_="editor-content") or art_soup.find("article", id="main-content") or art_soup

for li in info_container.find_all("li"):
    text = li.get_text(strip=True)
    text_lower = text.lower()
    
    if "zł" in text_lower and ("benzyna" in text_lower or "olej" in text_lower or "zł/l" in text_lower or "lpg" in text_lower):
        prices.append(text)

if prices:
    prices_text = "\n".join([f"• **{price}**" for price in prices])
else:
    print("⚠️ Nie znaleziono cen w formacie listy <ul>, szukam w tagu <p class='intro'>...")
    intro_tag = art_soup.find("p", class_="intro")
    if intro_tag:
        prices_text = f"*{intro_tag.get_text(strip=True)}*"
    else:
        print("❌ Nie znaleziono cen w artykule w żaden znany sposób.")
        sys.exit(0)

webhook_url = os.getenv("DISCORD_WEBHOOK")
if not webhook_url:
    print("DISCORD_WEBHOOK not set in .env file / secrets")
    sys.exit(1)

message = {
    "content": f"⛽ **Nowe ceny paliw!**\n*{found_title}*\n\n{prices_text}\n\n[🔗 Kliknij tutaj, aby otworzyć artykuł]({link_for_article})"
}

webhook_response = requests.post(webhook_url, json=message)

if webhook_response.status_code in (200, 204):
    print("Message sent successfully")
    with open(FILE_STATUS, "w", encoding="utf-8") as f:
        f.write(found_title)
else:
    print(f"Failed to send message. Status code: {webhook_response.status_code}")
    sys.exit(1)