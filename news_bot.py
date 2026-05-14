import os
import feedparser
import requests
import re
from datetime import datetime
from groq import Groq

# --- Konfiguration ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

groq_client = Groq(api_key=GROQ_API_KEY)

# --- RSS Feeds ---
FEEDS = {
    "🇩🇰 Danske nyheder": [
        "https://www.dr.dk/nyheder/service/feeds/allenyheder",
        "https://feeds.tv2.dk/news/rss",
        "https://politiken.dk/rss/",
        "https://www.berlingske.dk/rss",
        "https://www.jyllands-posten.dk/rss/",
    ],
    "🌍 Internationale nyheder": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss",
    ],
    "💻 Tech": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
    ],
    "📈 Finans": [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.ft.com/rss/home",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    ],
    "⚽ Sport": [
        "https://www.dr.dk/sporten/service/feeds/allesportsnyhedsartikler",
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.skysports.com/rss/12040",
    ],
}

MAX_ARTICLES_PER_CATEGORY = 8


def fetch_articles(feed_urls):
    articles = []
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ARTICLES_PER_CATEGORY]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                if title:
                    articles.append(f"- {title}: {summary}" if summary else f"- {title}")
        except Exception as e:
            print(f"Fejl ved hentning af {url}: {e}")
    return articles[:MAX_ARTICLES_PER_CATEGORY]


def summarize_with_groq(category, articles):
    if not articles:
        return "Ingen artikler fundet."

    articles_text = "\n".join(articles)
    prompt = f"""Du er en nyhedsredaktør der laver en kort morgenoversigt på dansk.

Her er dagens {category} nyheder:
{articles_text}

Opsummer de 4-5 vigtigste historier i korte, præcise punkter på dansk.
Vær konkret og informativ. Brug emoji sparsomt. Maks 400 ord."""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
    )
    return response.choices[0].message.content


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
        })
        if not response.ok:
            print(f"Telegram fejl: {response.text}")


def main():
    today = datetime.now().strftime("%A d. %d. %B %Y")
    full_message = f"☀️ Godmorgen! Her er nyhederne {today}\n\n"

    for category, feed_urls in FEEDS.items():
        print(f"Henter {category}...")
        articles = fetch_articles(feed_urls)
        summary = summarize_with_groq(category, articles)
        full_message += f"{category}\n{summary}\n\n"
        full_message += "---\n\n"

    full_message += "Hav en god dag!"

    print("Sender til Telegram...")
    send_telegram(full_message)
    print("Faerdig!")


if __name__ == "__main__":
    main()
