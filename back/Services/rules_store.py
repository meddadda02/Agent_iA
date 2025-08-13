import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

PG_CONN = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", 5432),
}

def get_latest_rules(limit=50):
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()
    cur.execute("""
        SELECT title, content, link, published_at
        FROM rules
        ORDER BY published_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "title": r[0],
            "content": r[1],
            "link": r[2],
            "published_at": r[3].isoformat() if r[3] else None
        }
        for r in rows
    ]
