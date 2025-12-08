import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import init_db, get_db, FoundCode, SteamAccount, SearchSource
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield

app = FastAPI(title="Steam Hunter", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RedeemRequest(BaseModel):
    code_id: int
    account_id: int | None = None

class ConfigReddit(BaseModel):
    client_id: str
    client_secret: str
    user_agent: str = "steam-hunter/1.0"

class ConfigSteamSession(BaseModel):
    cookies: dict
    account_name: str = "default"

@app.get("/api/codes")
def list_codes(
    status: str | None = None,
    code_type: str | None = None,
    source: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(FoundCode).order_by(desc(FoundCode.found_at))

    if status:
        query = query.filter(FoundCode.status == status)
    if code_type:
        query = query.filter(FoundCode.code_type == code_type)
    if source:
        query = query.filter(FoundCode.source.ilike(f"%{source}%"))

    codes = query.limit(limit).all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "code_type": c.code_type,
            "source": c.source,
            "source_url": c.source_url,
            "title": c.title,
            "status": c.status,
            "found_at": c.found_at.isoformat() if c.found_at else None,
            "redeemed_at": c.redeemed_at.isoformat() if c.redeemed_at else None,
            "error_message": c.error_message,
        }
        for c in codes
    ]

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(FoundCode).count()
    new = db.query(FoundCode).filter(FoundCode.status == "new").count()
    redeemed = db.query(FoundCode).filter(FoundCode.status == "redeemed").count()
    expired = db.query(FoundCode).filter(FoundCode.status == "expired").count()
    failed = db.query(FoundCode).filter(FoundCode.status == "failed").count()

    by_type = {}
    for row in db.query(FoundCode.code_type, FoundCode.status).all():
        key = f"{row.code_type}:{row.status}"
        by_type[key] = by_type.get(key, 0) + 1

    return {
        "total": total,
        "new": new,
        "redeemed": redeemed,
        "expired": expired,
        "failed": failed,
        "by_type": by_type,
    }

@app.post("/api/redeem")
def redeem_code(req: RedeemRequest, db: Session = Depends(get_db)):
    code_entry = db.query(FoundCode).filter(FoundCode.id == req.code_id).first()
    if not code_entry:
        raise HTTPException(404, "Code not found")

    if code_entry.status == "redeemed":
        raise HTTPException(400, "Code already redeemed")

    account = db.query(SteamAccount).filter(
        SteamAccount.id == (req.account_id or 1),
        SteamAccount.is_active == True,
    ).first()

    if not account or not account.session_cookies:
        raise HTTPException(400, "No active Steam account with session cookies configured")

    from .redeemer import redeem_key
    result = redeem_key(account.session_cookies, code_entry.code)

    if result["success"]:
        code_entry.status = "redeemed"
        code_entry.steam_account_id = account.id
        from datetime import datetime, timezone
        code_entry.redeemed_at = datetime.now(timezone.utc)
    else:
        code_entry.status = "failed"
        code_entry.error_message = result["message"]

    db.commit()
    return result

@app.post("/api/config/reddit")
def configure_reddit(config: ConfigReddit, db: Session = Depends(get_db)):
    source = db.query(SearchSource).filter(SearchSource.name == "reddit").first()
    if source:
        source.config = config.model_dump()
    else:
        source = SearchSource(
            name="reddit",
            source_type="reddit",
            config=config.model_dump(),
        )
        db.add(source)
    db.commit()

    from .scrapers.reddit import RedditScraper
    scraper = RedditScraper(config.client_id, config.client_secret, config.user_agent)
    posts = scraper.search_recent(limit=5)

    return {"message": "Reddit configured", "test_results": len(posts)}

@app.post("/api/config/steam-session")
def configure_steam(config: ConfigSteamSession, db: Session = Depends(get_db)):
    account = db.query(SteamAccount).filter(
        SteamAccount.name == config.account_name
    ).first()

    if account:
        account.session_cookies = config.cookies
    else:
        account = SteamAccount(
            name=config.account_name,
            session_cookies=config.cookies,
        )
        db.add(account)

    db.commit()
    return {"message": f"Steam account '{config.account_name}' configured"}

@app.get("/api/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(SearchSource).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": s.source_type,
            "enabled": s.enabled,
            "last_checked": s.last_checked.isoformat() if s.last_checked else None,
            "interval_minutes": s.interval_minutes,
        }
        for s in sources
    ]

@app.get("/api/accounts")
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(SteamAccount).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "is_active": a.is_active,
            "has_cookies": bool(a.session_cookies),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in accounts
    ]

@app.post("/api/codes/{code_id}/skip")
def skip_code(code_id: int, db: Session = Depends(get_db)):
    code = db.query(FoundCode).filter(FoundCode.id == code_id).first()
    if not code:
        raise HTTPException(404, "Code not found")
    code.status = "expired"
    db.commit()
    return {"message": "Code skipped"}
