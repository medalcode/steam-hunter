from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./steam_hunter.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class SteamAccount(Base):
    __tablename__ = "steam_accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), default="default")
    session_cookies = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class FoundCode(Base):
    __tablename__ = "found_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(255), nullable=True)
    code_type = Column(String(50))
    source = Column(String(255))
    source_url = Column(String(512), nullable=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="new")
    steam_account_id = Column(Integer, nullable=True)
    found_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    redeemed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

class SearchSource(Base):
    __tablename__ = "search_sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    source_type = Column(String(50))
    config = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    interval_minutes = Column(Integer, default=15)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
