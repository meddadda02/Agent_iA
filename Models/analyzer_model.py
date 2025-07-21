from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, Text,ForeignKey
from sqlalchemy.orm import relationship
from config import Base


class Analyzer(Base):
    __tablename__ = 'analyzer'

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    score = Column(String(50), nullable=True)
    toxic = Column(Boolean, nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())

    user_id = Column(Integer, ForeignKey('users.id'))  # Clé étrangère

    user = relationship("User", back_populates="analyzers")  # relation ORM

    def __repr__(self):
        return f"<Analyzer(id={self.id}, toxic={self.toxic}, date={self.date})>"
