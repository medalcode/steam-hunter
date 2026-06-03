import os
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
    validation_status = Column(String(20), nullable=True)
    validation_reason = Column(Text, nullable=True)

class SearchSource(Base):
    __tablename__ = "search_sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    source_type = Column(String(50))
    config = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    interval_minutes = Column(Integer, default=15)

class NotificationConfig(Base):
    __tablename__ = "notification_config"

    id = Column(Integer, primary_key=True)
    discord_webhook_url = Column(String(512), default="")
    telegram_bot_token = Column(String(256), default="")
    telegram_chat_id = Column(String(100), default="")
    notify_on_new = Column(Boolean, default=True)
    notify_on_redeem = Column(Boolean, default=False)
    notify_on_fail = Column(Boolean, default=True)

class ASFConfig(Base):
    __tablename__ = "asf_config"

    id = Column(Integer, primary_key=True)
    ipc_url = Column(String(256), default=os.environ.get("ASF_IPC_URL", "http://localhost:1243"))
    ipc_password = Column(String(256), default=os.environ.get("ASF_IPC_PASSWORD", ""))
    default_bot = Column(String(100), default=os.environ.get("ASF_DEFAULT_BOT", "principal"))
    auto_redeem = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(bind=engine)

    # Seed ASF config from environment variables if set
    ipc_url = os.environ.get("ASF_IPC_URL", "")
    ipc_password = os.environ.get("ASF_IPC_PASSWORD", "")
    default_bot = os.environ.get("ASF_DEFAULT_BOT", "")
    if ipc_url or ipc_password or default_bot:
        db = SessionLocal()
        try:
            cfg = db.query(ASFConfig).first()
            if not cfg:
                cfg = ASFConfig()
                db.add(cfg)
            if ipc_url:
                cfg.ipc_url = ipc_url
            if ipc_password:
                cfg.ipc_password = ipc_password
            if default_bot:
                cfg.default_bot = default_bot
            if os.environ.get("ASF_AUTO_REDEEM", "").lower() in ("1", "true", "yes"):
                cfg.auto_redeem = True
            db.commit()
        finally:
            db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
