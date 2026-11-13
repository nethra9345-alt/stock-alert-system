import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    symbol = Column(String(50), nullable=False, index=True)
    company_name = Column(String(200), nullable=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    overview_data = Column(JSON, nullable=True)
    fundamentals_data = Column(JSON, nullable=True)
    technical_data = Column(JSON, nullable=True)
    events_data = Column(JSON, nullable=True)
    risk_factors = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    conclusion = Column(Text, nullable=False)
    pdf_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", backref="research_reports")


class ResearchChatMessage(Base):
    __tablename__ = "research_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    session_id = Column(String(100), nullable=False, index=True)
    symbol = Column(String(50), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    retrieved_context = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", backref="research_messages")
