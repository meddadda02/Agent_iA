import feedparser
import psycopg2
import hashlib
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Postgres connection details from .env
PG_CONN = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", 5432),
}

# RSS sources (replace/add official YouTube policy feeds)
FEEDS = [
    "https://blog.youtube/news-and-events/rss/",
    "https://support.google.com/youtube/rss/answer/9288567"
]

def store_rule(entry, source):
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()

    content = entry.get("summary", "")
    title = entry.get("title", "")
    link = entry.get("link", "")
    published = entry.get("published_parsed")
    published_at = datetime(*published[:6]) if published else None

    # Deduplication hash
    rule_hash = hashlib.sha256((title + content).encode()).hexdigest()

    cur.execute("SELECT 1 FROM rules WHERE hash=%s", (rule_hash,))
    if cur.fetchone():
        conn.close()
        return

    cur.execute("""
        INSERT INTO rules (title, link, content, published_at, source, hash)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (title, link, content, published_at, source, rule_hash))
    conn.commit()
    conn.close()

def fetch_rules():
    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            store_rule(entry, feed_url)

if __name__ == "__main__":
    fetch_rules()
