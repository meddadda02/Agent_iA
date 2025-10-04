# back/Services/suggestion_service.py
import os, json, time, httpx
from typing import Any, Dict, List, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# --- Simple circuit breaker (like your ModerationService) ---
class CircuitBreaker:
    def __init__(self, timeout: int = 60, max_failures: int = 3):
        self.timeout = timeout
        self.max_failures = max_failures
        self.failures = 0
        self.last_failure = 0.0

    def ok(self) -> bool:
        if self.failures >= self.max_failures and time.time() - self.last_failure < self.timeout:
            return False
        if time.time() - self.last_failure > self.timeout:
            self.failures = 0
        return True

    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()


_cb = CircuitBreaker()


def _call_groq(messages: List[Dict[str, str]], model="gpt-4o-mini") -> Dict[str, Any]:
    if not _cb.ok():
        raise RuntimeError("Groq circuit open (too many failures)")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.2,
    }
    try:
        with httpx.Client(timeout=20.0) as c:
            r = c.post(GROQ_API_URL, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        _cb.record_failure()
        raise e


def generate_suggestions(
    rule_id: str,
    rule_title: str,
    violated_text: str,
    language: str = "fr",
    context_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calls Groq and returns structured JSON suggestions for a detected rule violation.
    """
    if context_metadata is None:
        context_metadata = {}

    system = {
        "role": "system",
        "content": (
            "Tu es un assistant expert en conformité et rédaction. "
            "Analyse la violation et propose des suggestions correctives pratiques. "
            "Retourne UNIQUEMENT du JSON conforme au schéma fourni."
        ),
    }

    user = {
        "role": "user",
        "content": (
            f"Règle détectée: {rule_id} - {rule_title}\n"
            f"Texte non conforme:\n'''{violated_text}'''\n\n"
            "Schema JSON attendu:\n"
            "{\n"
            "  \"rule_id\": string,\n"
            "  \"language\": \"fr\"|\"en\",\n"
            "  \"suggestions\": [\n"
            "    {\"id\": string, \"severity\": \"critical\"|\"major\"|\"minor\", "
            "\"short\": string, \"explanation\": string, "
            "\"actionable_steps\": [string], \"example_rewrite\": string}\n"
            "  ],\n"
            "  \"confidence\": number\n"
            "}\n"
            "Renvoie 2-4 suggestions concrètes et utiles. Sortie JSON uniquement."
        ),
    }

    try:
        data = _call_groq([system, user])
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        start, end = text.find("{"), text.rfind("}")
        parsed = json.loads(text[start:end+1]) if start != -1 and end != -1 else {}
        return {
            "rule_id": rule_id,
            "language": language,
            "suggestions": parsed.get("suggestions", []),
            "confidence": parsed.get("confidence"),
        }
    except Exception as e:
        return {"rule_id": rule_id, "language": language, "error": str(e), "suggestions": []}
