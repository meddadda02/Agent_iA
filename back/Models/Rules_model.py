from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Rules(BaseModel):
    id: str
    title: str
    link: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    source: Optional[str] = None
    hash: Optional[str] = None
    created_at: Optional[datetime] = None
    scope: Optional[str] = None
    prohibits: Optional[List[str]] = []
    allows_if: Optional[List[str]] = []
    examples_positive: Optional[List[str]] = []
    examples_negative: Optional[List[str]] = []
    keywords: Optional[List[str]] = []
