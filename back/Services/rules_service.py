# back/Services/rules_service.py
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("dbname"),
    "user": os.getenv("dbuser"),
    "password": os.getenv("dbpassword"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432))
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_rules_for_scope(scope: str):
    """Fetch active rules that apply to a given scope (video, audio, text, image)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, link, content, scope, prohibits, allows_if, keywords
                FROM rules
                WHERE scope @> ARRAY[%s]::text[]
            """, (scope,))
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "link": r[2],
            "content": r[3],
            "scope": r[4],
            "prohibits": r[5],
            "allows_if": r[6],
            "keywords": r[7]
        } for r in rows
    ]

# Example usage in moderation_service.py
from .rules_service import get_rules_for_scope

def moderate_content(content_text: str, scope: str):
    rules = get_rules_for_scope(scope)
    violations = []
    for rule in rules:
        for phrase in rule["prohibits"]:
            if phrase.lower() in content_text.lower():
                violations.append(rule["id"])
    return {
        "is_compliant": len(violations) == 0,
        "violated_rules": violations
    }
