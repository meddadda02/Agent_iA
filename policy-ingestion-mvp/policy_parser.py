import httpx
from selectolax.parser import HTMLParser
from datetime import datetime
import hashlib
import psycopg2

# === DB connection ===
conn = psycopg2.connect(
    dbname="agent_ai",  # change to your DB name
    user="postgres",    # change to your DB user
    password="salma",   # change to your password
    host="localhost",
    port=5432
)

MAIN_SELECTORS = [
    "article", "main", "div[role='main']"
]

def fetch_html(url: str) -> str:
    r = httpx.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def extract_main_text(html: str) -> str:
    tree = HTMLParser(html)
    for sel in MAIN_SELECTORS:
        node = tree.css_first(sel)
        if node and node.text():
            return node.text(separator="\n").strip()
    return tree.text(separator="\n").strip()

def store_rule(title, link, content, source):
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO rules (title, link, content, published_at, source, hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (hash) DO NOTHING
        """, (title, link, content, datetime.utcnow(), source, h))
    conn.commit()

def to_rule_doc(url: str):
    html = fetch_html(url)
    text = extract_main_text(html)
    tree = HTMLParser(html)
    title_node = tree.css_first("h1")
    title = title_node.text().strip() if title_node else url

    # store in DB
    store_rule(title, url, text, "youtube")
    print(f"Inserted: {title}")

if __name__ == "__main__":
    from sitemap_crawler import get_catalog
    urls = get_catalog()
    for entry in urls:
        to_rule_doc(entry["loc"])
    print("✅ All policies processed and stored.")
