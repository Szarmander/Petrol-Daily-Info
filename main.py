from datetime import datetime
from zoneinfo import ZoneInfo
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

today = datetime.now(ZoneInfo("Europe/Warsaw"))
months = {
    1: "stycznia",
    2: "lutego",
    3: "marca",
    4: "kwietnia",
    5: "maja",
    6: "czerwca",
    7: "lipca",
    8: "sierpnia",
    9: "września",
    10: "października",
    11: "listopada",
    12: "grudnia"
}

looking_date = f"{today.day} {months[today.month]} {today.year}"

FILE_STATUS = "status.txt"

if(os.path.exists(FILE_STATUS)):
    with open(FILE_STATUS, "r", encoding="utf-8") as f:
        last_date = f.read().strip()
        if last_date == looking_date:
            print("Already checked today")
            sys.exit(0)

BASE_URL = "https://www.gov.pl"
NEWS_URL = f"{BASE_URL}/web/energia/wiadomosci"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("Searching for article with date ", looking_date)
response = requests.get(NEWS_URL, headers=headers)
soup = BeautifulSoup(response.content, "html.parser")

link_for_article = None
looking_phrase = f"Maksymalna cena detaliczna paliw obowiązująca {looking_date}"

for a in soup.find_all("a", href=True):
    title = a.get_text(strip=True)
    if looking_phrase.lower() in title.lower():
        link_for_article = a.get("href")
        break

if not link_for_article:
    print("Article not found")
    sys.exit(0)

if not link_for_article.startswith("http"):
    link_for_article = BASE_URL + link_for_article

art_response = requests.get(link_for_article, headers=headers)
art_soup = BeautifulSoup(art_response.content, "html.parser")

prices = []
info_container = art_soup.find("div", class_="editor-content")
ul_list = info_container.find("ul")

if ul_list:
    for li in ul_list.find_all("li"):
        prices.append(li.get_text(strip=True))

if not prices:
    prices_text = "Finded article but not finded prices"
    sys.exit(0)
else:
    prices_text = "\n".join([f"• **{price}**" for price in prices])

webhook_url = os.getenv("DISCORD_WEBHOOK")
if not webhook_url:
    print("DISCORD_WEBHOOK not set in .env file")
    sys.exit(1)

message = {
    "content": f"⛽ **Nowe maksymalne ceny paliw na dzień {looking_date}!**\n\n{prices_text}\n\n[🔗 Kliknij tutaj, aby otworzyć artykuł]({link_for_article})"
}

webhook_response = requests.post(webhook_url, json=message)

if webhook_response.status_code in (200, 204):
    print("Message sent successfully")
    with open(FILE_STATUS, "w", encoding="utf-8") as f:
        f.write(looking_date)
else:
    print(f"Failed to send message. Status code: {webhook_response.status_code}")
    sys.exit(1)
