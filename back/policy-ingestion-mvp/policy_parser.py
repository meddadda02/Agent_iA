import httpx
from selectolax.parser import HTMLParser
from datetime import datetime
import hashlib
import psycopg2
from sitemap_crawler import get_catalog
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
# === DB connection ===
conn = psycopg2.connect(
    dbname=os.getenv("dbname"),   # nom database depuis .env
    user="postgres",
    password=os.getenv("dbpassword"), #password database from .env 
    host="localhost",
    port=5432
)

MAIN_SELECTORS = ["article", "main", "div[role='main']"]

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

def guess_scope(text: str):
    scopes = []
    lower = text.lower()
    if any(word in lower for word in ["video", "live stream", "broadcast"]):
        scopes.append("video")
    if "thumbnail" in lower:
        scopes.extend(["image", "thumbnail"])
    if any(word in lower for word in ["comment", "post", "chat"]):
        scopes.append("comments")
    if any(word in lower for word in ["audio", "song", "music"]):
        scopes.append("audio")
    if any(word in lower for word in ["description", "title", "text"]):
        scopes.append("text")
    return list(set(scopes)) or ["text","video","audio","image"]

def store_rule(title, link, content, source):
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    scope = guess_scope(content)
    prohibits = []  # placeholder: can be filled by NLP/regex extraction
    allows_if = []
    examples_positive = []
    examples_negative = []

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO rules (title, link, content, published_at, source, hash, scope, prohibits, allows_if, examples_positive, examples_negative)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (hash) DO UPDATE SET
            scope = EXCLUDED.scope,
            prohibits = EXCLUDED.prohibits,
            allows_if = EXCLUDED.allows_if,
            examples_positive = EXCLUDED.examples_positive,
            examples_negative = EXCLUDED.examples_negative

        """, (
            title, link, content, datetime.utcnow(), source, h,
            scope, prohibits, allows_if, examples_positive, examples_negative
        ))
    conn.commit()

def to_rule_doc(url: str):
    html = fetch_html(url)
    text = extract_main_text(html)
    tree = HTMLParser(html)
    title_node = tree.css_first("h1")
    title = title_node.text().strip() if title_node else url
    store_rule(title, url, text, "youtube")
    print(f"Processed: {title}")

if __name__ == "__main__":
    urls = get_catalog()
    for entry in urls:
        to_rule_doc(entry["loc"])
    print("✅ Ingestion complete.")
