from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ARRAY
from config import Base, get_db


class Rules(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    link = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    published_at = Column(TIMESTAMP, nullable=True)
    source = Column(Text, nullable=True)
    hash = Column(Text, unique=True, nullable=False)
    scope = Column(ARRAY(Text), default=[])
    prohibits = Column(ARRAY(Text), default=[])
    allows_if = Column(ARRAY(Text), default=[])
    examples_positive = Column(ARRAY(Text), default=[])
    examples_negative = Column(ARRAY(Text), default=[])
    keywords = Column(Text, nullable=True)