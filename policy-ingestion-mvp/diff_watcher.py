
import difflib, json, hashlib
from pathlib import Path

def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def changed(old_text: str, new_text: str) -> bool:
    return text_hash(old_text) != text_hash(new_text)

def unified_diff(a: str, b: str) -> str:
    return "\n".join(difflib.unified_diff(
        a.splitlines(), b.splitlines(), lineterm=""
    ))
