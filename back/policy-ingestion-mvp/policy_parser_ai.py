import httpx
from selectolax.parser import HTMLParser
from datetime import datetime
import hashlib
import psycopg2
import spacy
import yake
import re
from sitemap_crawler import get_catalog
import os
from dotenv import load_dotenv

# Load env (optional, you can hardcode if you prefer)
load_dotenv()

# --- DB connection (kept as you had it) ---
conn = psycopg2.connect(
    dbname=os.getenv("dbname"),
    user="postgres",
    password=os.getenv("dbpassword"),
    host="localhost",
    port=5432
)

# NLP models
nlp = spacy.load("en_core_web_sm")
kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=15)

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

def ai_extract_fields(text: str):
    doc = nlp(text)

    # Guess scope based on keywords
    scope = []
    lower = text.lower()
    if any(word in lower for word in ["video", "live stream", "broadcast"]):
        scope.append("video")
    if "thumbnail" in lower:
        scope.extend(["image", "thumbnail"])
    if any(word in lower for word in ["comment", "post", "chat"]):
        scope.append("comments")
    if any(word in lower for word in ["audio", "song", "music"]):
        scope.append("audio")
    if any(word in lower for word in ["description", "title", "text"]):
        scope.append("text")
    if not scope:
        scope = ["text", "video", "audio", "image"]

    # Extract prohibitions
    prohibits = [s.text.strip()
                 for s in doc.sents
                 if re.search(r"prohibit|forbid|not allowed|must not", s.text, re.I)]

    # Extract conditional allowances
    allows_if = [s.text.strip()
                 for s in doc.sents
                 if re.search(r"allowed if|permitted if|can.*if", s.text, re.I)]

    # Keywords
    keywords = [kw for kw, _ in kw_extractor.extract_keywords(text)]

    return scope, prohibits, allows_if, keywords

def store_rule(title, link, content, source):
    # Keep content hash (useful for updates/debug)
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()

    scope, prohibits, allows_if, keywords = ai_extract_fields(content)

    with conn.cursor() as cur:
        # IMPORTANT: de-duplicate on LINK (you already have a unique constraint on link)
        cur.execute("""
            INSERT INTO rules (title, link, content, published_at, source, hash, scope, prohibits, allows_if, keywords)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (link) DO UPDATE SET
                content      = EXCLUDED.content,
                published_at = EXCLUDED.published_at,
                source       = EXCLUDED.source,
                hash         = EXCLUDED.hash,
                scope        = EXCLUDED.scope,
                prohibits    = EXCLUDED.prohibits,
                allows_if    = EXCLUDED.allows_if,
                keywords     = EXCLUDED.keywords
        """, (
            title, link, content, datetime.utcnow(), source, h,
            scope, prohibits, allows_if, keywords
        ))
    conn.commit()

def to_rule_doc(url: str):
    html = fetch_html(url)
    text = extract_main_text(html)
    tree = HTMLParser(html)
    title_node = tree.css_first("h1")
    title = title_node.text().strip() if title_node else url
    store_rule(title, url, text, "youtube")
    print(f"✅ Processed: {title}")

if __name__ == "__main__":
    urls = get_catalog()
    for entry in urls:
        try:
            to_rule_doc(entry["loc"])
        except Exception as e:
            # Don't crash the batch if one page fails
            print(f"⚠️ Skipped {entry.get('loc')} due to error: {e}")
    print("✅ Ingestion complete.")
