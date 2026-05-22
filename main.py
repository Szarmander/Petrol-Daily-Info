import os
import sys
import requests
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
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("Searching for the latest fuel prices article...")
response = requests.get(NEWS_URL, headers=headers)
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

art_response = requests.get(link_for_article, headers=headers)
art_soup = BeautifulSoup(art_response.content, "html.parser")

prices = []
info_container = art_soup.find("div", class_="editor-content") or art_soup.find("article")

if info_container:
    ul_list = info_container.find("ul")
    if ul_list:
        for li in ul_list.find_all("li"):
            prices.append(li.get_text(strip=True))

if not prices:
    print("Found article but not found prices")
    sys.exit(0)
else:
    prices_text = "\n".join([f"• **{price}**" for price in prices])

webhook_url = os.getenv("DISCORD_WEBHOOK")
if not webhook_url:
    print("DISCORD_WEBHOOK not set in .env file")
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