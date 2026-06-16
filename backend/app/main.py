import csv
import io
import json
import logging
import os
import secrets
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import init_db, get_db, FoundCode, SteamAccount, SearchSource, NotificationConfig, ASFConfig, APIKey
from .scheduler import start_scheduler, set_websocket_manager, run_scrapers_once, cleanup_old_entries
from .mcp_server import create_sse_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from cachetools import TTLCache

# Simple TTL rate limiter to prevent memory leaks
_rate_limit_store = TTLCache(maxsize=10000, ttl=60)
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60

def _check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Get existing hits for this IP, or initialize an empty list
    window = _rate_limit_store.get(client_ip, [])
    
    # Filter out old hits
    window = [t for t in window if now - t < RATE_LIMIT_WINDOW]
    
    if len(window) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        
    window.append(now)
    _rate_limit_store[client_ip] = window

_API_KEY_ENV = os.environ.get("STEAM_HUNTER_API_KEY", "")

def _check_api_key(request: Request, db: Session = Depends(get_db)):
    if not _API_KEY_ENV:
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if token == _API_KEY_ENV:
            return True
        key_entry = db.query(APIKey).filter(APIKey.key == token, APIKey.is_active == True).first()
        if key_entry:
            return True
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    def broadcast(self, data: dict):
        for ws in self.active.copy():
            try:
                import asyncio
                asyncio.create_task(ws.send_json(data))
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()
set_websocket_manager(manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield

app = FastAPI(title="Steam Hunter", lifespan=lifespan)

mcp_sse_app = create_sse_app()
app.mount("/mcp", mcp_sse_app)

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    asf_cfg = db.query(ASFConfig).first()
    bots_online = 0
    if asf_cfg and asf_cfg.ipc_url:
        from .asf_client import ASFClient
        asf = ASFClient(asf_cfg.ipc_url, asf_cfg.ipc_password)
        bots = asf.get_bots()
        bots_online = sum(1 for b in bots if b.get("online"))
    total = db.query(FoundCode).count()
    redeemed = db.query(FoundCode).filter(FoundCode.status == "redeemed").count()
    pending = db.query(FoundCode).filter(FoundCode.status == "new").count()
    return {
        "status": "ok",
        "bots_online": bots_online,
        "total_codes": total,
        "redeemed": redeemed,
        "pending": pending,
        "scheduler_running": hasattr(app.state, "scheduler") and app.state.scheduler.running if hasattr(app.state, "scheduler") else True,
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCLUDED_AUTH_PATHS = {"/api/health", "/mcp/sse", "/mcp/messages/", "/docs", "/openapi.json", "/ws"}

@app.middleware("http")
async def rate_limit_and_auth_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        _check_rate_limit(request)
    if path in EXCLUDED_AUTH_PATHS or path.startswith("/mcp/") or path.startswith("/ws"):
        return await call_next(request)
    if not _API_KEY_ENV:
        return await call_next(request)
    from starlette.responses import JSONResponse
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if token == _API_KEY_ENV:
            return await call_next(request)
        db = next(get_db())
        try:
            key_entry = db.query(APIKey).filter(APIKey.key == token, APIKey.is_active == True).first()
            if key_entry:
                return await call_next(request)
        finally:
            db.close()
    return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

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

class AccountCreate(BaseModel):
    name: str
    cookies: dict

class NotifConfigUpdate(BaseModel):
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    notify_on_new: bool = True
    notify_on_redeem: bool = False
    notify_on_fail: bool = True

def code_to_dict(c: FoundCode) -> dict:
    return {
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
        "validation_status": c.validation_status,
        "validation_reason": c.validation_reason,
        "steam_account_id": c.steam_account_id,
    }

# ─── WebSocket ───────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)

# ─── Codes ──────────────────────────────────────────────────

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
    return [code_to_dict(c) for c in query.limit(limit).all()]

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
        code_entry.redeemed_at = datetime.now(timezone.utc)
    else:
        code_entry.status = "failed"
        code_entry.error_message = result["message"]

    db.commit()
    return result

@app.post("/api/scrape")
def trigger_scrape():
    from .database import SessionLocal as DbSession, SearchSource

    reddit_scraper = None
    db_cfg = DbSession()
    try:
        source = db_cfg.query(SearchSource).filter(SearchSource.name == "reddit").first()
        if source and source.config:
            from .scrapers.reddit import RedditScraper
            cfg = source.config
            reddit_scraper = RedditScraper(
                cfg.get("client_id", ""),
                cfg.get("client_secret", ""),
                cfg.get("user_agent", "steam-hunter/1.0"),
            )
    finally:
        db_cfg.close()

    import time
    start = time.time()
    entries = run_scrapers_once(reddit_scraper=reddit_scraper)
    elapsed = time.time() - start

    return {"status": "ok", "new_entries": len(entries), "elapsed_seconds": round(elapsed, 1)}

@app.post("/api/cleanup")
def trigger_cleanup():
    cleanup_old_entries()
    return {"status": "ok", "message": "Cleanup completed"}

@app.post("/api/asf/retry-failed")
def retry_failed_redeems(bot: str | None = None, db: Session = Depends(get_db)):
    client, config = get_asf_client(db)
    bot_name = bot or config.default_bot

    pending = db.query(FoundCode).filter(
        FoundCode.code_type == "key",
        FoundCode.status.in_(["failed", "retry"]),
    ).limit(20).all()

    results = []
    for code_entry in pending:
        codes = [c.strip() for c in code_entry.code.replace(",", " ").split()]
        for key in codes:
            result = client.redeem_key(bot_name, key)
            results.append({"code_id": code_entry.id, "key": key, **result})
            if result.get("success"):
                code_entry.status = "redeemed"
                code_entry.redeemed_at = datetime.now(timezone.utc)
                code_entry.error_message = None
            elif result.get("status") in ("duplicate", "invalid"):
                code_entry.status = "failed"
                code_entry.error_message = result.get("message", "")
            elif result.get("status") == "retry":
                code_entry.status = "retry"
                code_entry.error_message = result.get("message", "Transient error")
            else:
                code_entry.status = "failed"
                code_entry.error_message = result.get("message", "Retry failed")
        db.commit()

    return {"total": len(pending), "results": results}

@app.post("/api/codes/{code_id}/skip")
def skip_code(code_id: int, db: Session = Depends(get_db)):
    code = db.query(FoundCode).filter(FoundCode.id == code_id).first()
    if not code:
        raise HTTPException(404, "Code not found")
    code.status = "expired"
    db.commit()
    return {"message": "Code skipped"}

# ─── Export ─────────────────────────────────────────────────

@app.get("/api/export/json")
def export_json(
    status: str | None = None,
    code_type: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(FoundCode).order_by(desc(FoundCode.found_at))
    if status:
        query = query.filter(FoundCode.status == status)
    if code_type:
        query = query.filter(FoundCode.code_type == code_type)

    codes = [code_to_dict(c) for c in query.all()]
    return StreamingResponse(
        io.StringIO(json.dumps(codes, indent=2, default=str)),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=steam_codes.json"},
    )

@app.get("/api/export/csv")
def export_csv(
    status: str | None = None,
    code_type: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(FoundCode).order_by(desc(FoundCode.found_at))
    if status:
        query = query.filter(FoundCode.status == status)
    if code_type:
        query = query.filter(FoundCode.code_type == code_type)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "code", "type", "source", "title", "status", "found_at", "redeemed_at", "validation"])
    for c in query.all():
        writer.writerow([
            c.id, c.code, c.code_type, c.source, c.title,
            c.status, c.found_at, c.redeemed_at, c.validation_status,
        ])

    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=steam_codes.csv"},
    )

# ─── Validate ───────────────────────────────────────────────

# ─── ASF ────────────────────────────────────────────────────

class ASFConfigUpdate(BaseModel):
    ipc_url: str = "http://localhost:1242"
    ipc_password: str = ""
    default_bot: str = "principal"
    auto_redeem: bool = False

class ASFRedeemRequest(BaseModel):
    code_id: int
    bot: str | None = None

def get_asf_client(db: Session) -> tuple:
    config = db.query(ASFConfig).first()
    if not config:
        config = ASFConfig()
        db.add(config)
        db.commit()
    from .asf_client import ASFClient
    return ASFClient(config.ipc_url, config.ipc_password), config

@app.get("/api/config/asf")
def get_asf_config(db: Session = Depends(get_db)):
    config = db.query(ASFConfig).first()
    if not config:
        config = ASFConfig()
        db.add(config)
        db.commit()
    return {
        "ipc_url": config.ipc_url,
        "ipc_password": bool(config.ipc_password),
        "default_bot": config.default_bot,
        "auto_redeem": config.auto_redeem,
    }

@app.post("/api/config/asf")
def update_asf_config(config_in: ASFConfigUpdate, db: Session = Depends(get_db)):
    config = db.query(ASFConfig).first()
    if not config:
        config = ASFConfig()
        db.add(config)
    config.ipc_url = config_in.ipc_url
    config.ipc_password = config_in.ipc_password
    config.default_bot = config_in.default_bot
    config.auto_redeem = config_in.auto_redeem
    db.commit()
    return {"message": "ASF config saved"}

@app.get("/api/asf/bots")
def list_asf_bots(db: Session = Depends(get_db)):
    client, _ = get_asf_client(db)
    bots = client.get_bots()
    return bots

@app.post("/api/asf/redeem")
def asf_redeem(req: ASFRedeemRequest, db: Session = Depends(get_db)):
    client, config = get_asf_client(db)
    bot = req.bot or config.default_bot

    code_entry = db.query(FoundCode).filter(FoundCode.id == req.code_id).first()
    if not code_entry:
        raise HTTPException(404, "Code not found")
    if code_entry.status == "redeemed":
        raise HTTPException(400, "Code already redeemed")
    if code_entry.code_type != "key":
        raise HTTPException(400, "Only keys can be redeemed via ASF")

    codes = [c.strip() for c in code_entry.code.replace(",", " ").split()]
    results = []
    for key in codes:
        result = client.redeem_key(bot, key)
        results.append({"key": key, **result})

    any_success = any(r["success"] for r in results)
    if any_success:
        code_entry.status = "redeemed"
        code_entry.redeemed_at = datetime.now(timezone.utc)
        code_entry.error_message = None
    else:
        all_retry = all(r.get("status") == "retry" for r in results)
        code_entry.status = "retry" if all_retry else "failed"
        code_entry.error_message = results[0].get("message", "ASF redeem failed") if results else "No keys"

    db.commit()

    manager.broadcast({"type": "redeem_result", "code_id": req.code_id, "status": code_entry.status})

    return {"results": results, "final_status": code_entry.status}

@app.post("/api/asf/redeem-all")
def asf_redeem_all(bot: str | None = None, db: Session = Depends(get_db)):
    client, config = get_asf_client(db)
    bot_name = bot or config.default_bot

    pending = db.query(FoundCode).filter(
        FoundCode.code_type == "key",
        FoundCode.status.in_(["new", "retry"]),
    ).limit(20).all()

    results = []
    for code_entry in pending:
        codes = [c.strip() for c in code_entry.code.replace(",", " ").split()]
        for key in codes:
            result = client.redeem_key(bot_name, key)
            results.append({"code_id": code_entry.id, "key": key, **result})
            if result.get("success"):
                code_entry.status = "redeemed"
                code_entry.redeemed_at = datetime.now(timezone.utc)
                code_entry.error_message = None
            elif result.get("status") in ("duplicate", "invalid"):
                code_entry.status = "failed"
                code_entry.error_message = result["message"]
            elif result.get("status") == "retry":
                code_entry.status = "retry"
                code_entry.error_message = result.get("message", "Transient error")
            else:
                code_entry.status = "failed"
                code_entry.error_message = result.get("message", "Unknown error")

    db.commit()

    if results:
        manager.broadcast({"type": "bulk_redeem", "count": len(results)})

    return {"total": len(pending), "results": results}

# ─── Validate ───────────────────────────────────────────────

@app.post("/api/validate/{code_id}")
def validate_code(code_id: int, db: Session = Depends(get_db)):
    code_entry = db.query(FoundCode).filter(FoundCode.id == code_id).first()
    if not code_entry:
        raise HTTPException(404, "Code not found")

    from .validator import validate_key_format, validate_gift_link
    if code_entry.code_type == "key":
        result = validate_key_format(code_entry.code)
    elif code_entry.code_type == "gift_link":
        result = validate_gift_link(code_entry.code)
    else:
        result = {"valid": True, "reason": "Giveaway link (no automated validation)"}

    code_entry.validation_status = "valid" if result["valid"] else "invalid"
    code_entry.validation_reason = result["reason"][:500]
    db.commit()
    return result

# ─── Auto-enter ────────────────────────────────────────────

class AutoEnterRequest(BaseModel):
    url: str
    title: str = ""

@app.post("/api/auto-enter")
def auto_enter_giveaway(req: AutoEnterRequest):
    from .auto_enter import auto_enter_giveaway as do_enter
    return do_enter(req.url, req.title)

# ─── Config ─────────────────────────────────────────────────

@app.post("/api/config/reddit")
def configure_reddit(config: ConfigReddit, db: Session = Depends(get_db)):
    source = db.query(SearchSource).filter(SearchSource.name == "reddit").first()
    if source:
        source.config = config.model_dump()
    else:
        source = SearchSource(name="reddit", source_type="reddit", config=config.model_dump())
        db.add(source)
    db.commit()

    from .scrapers.reddit import RedditScraper
    scraper = RedditScraper(config.client_id, config.client_secret, config.user_agent)
    posts = scraper.search_recent(limit=5)
    return {"message": "Reddit configured", "test_results": len(posts)}

@app.post("/api/config/steam-session")
def configure_steam(config: ConfigSteamSession, db: Session = Depends(get_db)):
    account = db.query(SteamAccount).filter(SteamAccount.name == config.account_name).first()
    if account:
        account.session_cookies = config.cookies
    else:
        account = SteamAccount(name=config.account_name, session_cookies=config.cookies)
        db.add(account)
    db.commit()
    return {"message": f"Steam account '{config.account_name}' configured"}

@app.get("/api/config/notifications")
def get_notification_config(db: Session = Depends(get_db)):
    config = db.query(NotificationConfig).first()
    if not config:
        config = NotificationConfig()
        db.add(config)
        db.commit()
    return {
        "discord_webhook_url": config.discord_webhook_url,
        "telegram_bot_token": config.telegram_bot_token,
        "telegram_chat_id": config.telegram_chat_id,
        "notify_on_new": config.notify_on_new,
        "notify_on_redeem": config.notify_on_redeem,
        "notify_on_fail": config.notify_on_fail,
    }

@app.post("/api/config/notifications")
def update_notification_config(config: NotifConfigUpdate, db: Session = Depends(get_db)):
    notif = db.query(NotificationConfig).first()
    if not notif:
        notif = NotificationConfig()
        db.add(notif)
    notif.discord_webhook_url = config.discord_webhook_url
    notif.telegram_bot_token = config.telegram_bot_token
    notif.telegram_chat_id = config.telegram_chat_id
    notif.notify_on_new = config.notify_on_new
    notif.notify_on_redeem = config.notify_on_redeem
    notif.notify_on_fail = config.notify_on_fail
    db.commit()
    return {"message": "Notification config updated"}

# ─── Sources ────────────────────────────────────────────────

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

@app.post("/api/sources/{source_id}/toggle")
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(SearchSource).filter(SearchSource.id == source_id).first()
    if not source:
        raise HTTPException(404, "Source not found")
    source.enabled = not source.enabled
    db.commit()
    return {"enabled": source.enabled}

# ─── Accounts ───────────────────────────────────────────────

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

@app.post("/api/accounts")
def create_account(acct: AccountCreate, db: Session = Depends(get_db)):
    account = SteamAccount(name=acct.name, session_cookies=acct.cookies)
    db.add(account)
    db.commit()
    return {"message": f"Account '{acct.name}' created", "id": account.id}

@app.post("/api/accounts/{account_id}/toggle")
def toggle_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(SteamAccount).filter(SteamAccount.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    account.is_active = not account.is_active
    db.commit()
    return {"is_active": account.is_active}

@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(SteamAccount).filter(SteamAccount.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()
    return {"message": "Account deleted"}
