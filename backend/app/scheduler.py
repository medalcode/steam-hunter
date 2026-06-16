import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

import requests as http_requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

STEAM_APP_RE = re.compile(r"store\.steampowered\.com/app/(\d+)")

# Scraper backoff: skip dead sources after N consecutive failures
_scraper_cooldowns: dict[str, float] = {}
SCRAPER_BACKOFF_MINUTES = 120  # skip for 2 hours after failure

def _should_skip_scraper(name: str) -> bool:
    last_fail = _scraper_cooldowns.get(name, 0)
    if last_fail == 0:
        return False
    elapsed = time.time() - last_fail
    if elapsed < SCRAPER_BACKOFF_MINUTES * 60:
        logger.info(f"{name}: skipping (cooldown {int(elapsed/60)}/{SCRAPER_BACKOFF_MINUTES} min)")
        return True
    return False

def _record_scraper_failure(name: str):
    was_active = name not in _scraper_cooldowns
    _scraper_cooldowns[name] = time.time()
    logger.info(f"{name}: recorded failure, entering cooldown")
    if was_active:
        _notify_scraper_cooldown(name)

def _record_scraper_success(name: str):
    _scraper_cooldowns.pop(name, None)


def _notify_scraper_cooldown(name: str):
    from .database import SessionLocal, NotificationConfig as DBNotifConfig
    from .notifications import Notifier, NotificationConfig as NotifCfg
    db = SessionLocal()
    try:
        cfg = db.query(DBNotifConfig).first()
        if not cfg or not (cfg.discord_webhook_url or cfg.telegram_bot_token):
            return
        notifier = Notifier(NotifCfg(
            discord_webhook_url=cfg.discord_webhook_url or "",
            telegram_bot_token=cfg.telegram_bot_token or "",
            telegram_chat_id=cfg.telegram_chat_id or "",
        ))
        notifier.send(
            "⚠️ Scraper en cooldown",
            f"El scraper '{name}' falló reiteradamente y entrará en cooldown de {SCRAPER_BACKOFF_MINUTES} minutos.",
        )
    finally:
        db.close()

def _get_free_sub(app_id: str) -> str | None:
    """Fetch the free promotional sub ID for a Steam app."""
    try:
        resp = http_requests.get(
            f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=en",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        if resp.status_code != 200:
            return None
        data = resp.json().get(app_id, {}).get("data", {})
        if not data.get("is_free"):
            return None
        for group in data.get("package_groups", []):
            for sub in group.get("subs", []):
                if sub.get("price", {}).get("initial", -1) == 0:
                    return str(sub["packageid"])
        for pid in data.get("packages", []):
            return str(pid)
    except Exception as e:
        logger.warning(f"Failed to get free sub for app {app_id}: {e}")
    return None

scheduler = BackgroundScheduler(daemon=True)

_websocket_manager = None

def set_websocket_manager(manager):
    global _websocket_manager
    _websocket_manager = manager

def get_notification_config(db):
    from .database import NotificationConfig
    config = db.query(NotificationConfig).first()
    if not config:
        config = NotificationConfig()
        db.add(config)
        db.commit()
    return config

def run_scrapers_once(reddit_scraper=None):
    from .database import SessionLocal, FoundCode, ASFConfig
    from .parser import parse_all
    from .scrapers.steamdb import SteamDBScraper
    from .scrapers.steam_store import SteamStoreScraper
    from .scrapers.steamgifts import SteamGiftsScraper
    from .scrapers.twitter import TwitterScraper
    from .scrapers.telegram_scraper import TelegramScraper
    from .scrapers.keysites import KeySitesScraper
    from .scrapers.moresources import MoreSourcesScraper
    from .scrapers.giveaway_apis import GiveawayAPIScraper
    from .scrapers.xbox import XboxScraper
    from .scrapers.xbox_catalog import XboxCatalogScraper
    from .scrapers.gog import GOGScraper
    from .validator import validate_key_format, validate_gift_link
    from .notifications import Notifier, NotificationConfig as NotifCfg

    twitter_scraper = TwitterScraper()
    steamdb_scraper = SteamDBScraper()
    steamgifts_scraper = SteamGiftsScraper()
    telegram_scraper = TelegramScraper()
    keysites_scraper = KeySitesScraper()
    moresources_scraper = MoreSourcesScraper()
    steam_scraper = SteamStoreScraper()
    giveaway_api_scraper = GiveawayAPIScraper()
    xbox_scraper = XboxScraper()
    xbox_catalog_scraper = XboxCatalogScraper()
    gog_scraper = GOGScraper()

    db = SessionLocal()
    try:
        notif_config = get_notification_config(db)
        notifier = Notifier(NotifCfg(
            discord_webhook_url=notif_config.discord_webhook_url or "",
            telegram_bot_token=notif_config.telegram_bot_token or "",
            telegram_chat_id=notif_config.telegram_chat_id or "",
        ))

        all_results = []

        scrapers_config = [
            ("Steam Freebies", steam_scraper.search_freebies),
            ("Steam F2P", steam_scraper.get_permanent_free),
            ("Freebie APIs", giveaway_api_scraper.search_all),
            ("CheapShark/Epic/More", moresources_scraper.search_all),
            ("Xbox Freebies", xbox_scraper.search_freebies),
            ("Xbox Catalog", xbox_catalog_scraper.search_freebies),
            ("GOG Freebies", gog_scraper.search_freebies),
            ("Telegram", telegram_scraper.search_channels),
            ("Key Sites", keysites_scraper.search_all),
            ("SteamGifts", steamgifts_scraper.get_giveaways),
            ("Twitter", twitter_scraper.search_giveaways),
            ("Reddit", lambda: reddit_scraper.search_recent() if reddit_scraper else []),
            ("SteamDB Free", steamdb_scraper.get_free_promotions),
            ("SteamDB Giveaways", steamdb_scraper.get_giveaways),
        ]

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_map = {}
            for name, scrape_fn in scrapers_config:
                if _should_skip_scraper(name):
                    continue
                future = executor.submit(scrape_fn)
                future_map[future] = name
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    results = future.result(timeout=60)
                    all_results.extend(results)
                    logger.info(f"{name}: {len(results)} results")
                    _record_scraper_success(name)
                except Exception as e:
                    logger.error(f"{name} scrape failed: {e}")
                    _record_scraper_failure(name)

        GIVEAWAY_SOURCES = {
            "gamerpower", "giveaway.su", "steamgifts",
            "steamdb", "steam/specials", "epic/free",
            "cheapshark/free", "cheapshark/deals",
            "fanatical/free", "freesteamkeys", "giveeclub",
            "xbox/free",
            "gog/free",
        }

        new_entries = []
        for result in all_results:
            parsed = parse_all(result.get("title", "") + " " + result.get("description", ""))
            source_url = result.get("source_url", "")
            title = result.get("title", "")
            source = result.get("source", "")

            has_inline = bool(parsed["keys"] or parsed["gift_links"] or parsed["giveaway_links"])
            has_url_giveaway = bool(
                source_url
                and ("giveaway" in source_url.lower() or "gamerpower.com" in source_url.lower())
            )
            is_known_source = any(
                s in source.lower() for s in GIVEAWAY_SOURCES
            ) or source.lower().startswith("r/")

            if not has_inline and not has_url_giveaway and not is_known_source:
                continue

            existing = db.query(FoundCode).filter(
                FoundCode.source_url == source_url,
                FoundCode.status != "expired",
            ).first()
            if existing:
                continue

            if has_inline:
                all_codes = parsed["keys"] + parsed["gift_links"] + parsed["giveaway_links"]
            else:
                all_codes = [source_url]

            for code in all_codes:
                code_type = (
                    "key" if ("-" in code and len(code) > 10)
                    else "gift_link" if "gift" in code or "friend" in code
                    else "giveaway"
                )

                validation = {"valid": True, "reason": ""}
                if code_type == "key":
                    validation = validate_key_format(code)
                elif code_type == "gift_link":
                    validation = validate_gift_link(code)

                entry = FoundCode(
                    code=code,
                    code_type=code_type,
                    source=result["source"],
                    source_url=source_url,
                    title=title,
                    description=result.get("description"),
                    status="new",
                    validation_status="valid" if validation["valid"] else "invalid",
                    validation_reason=validation["reason"][:500],
                )
                db.add(entry)
                new_entries.append(entry)

            db.commit()

            if new_entries:
                try:
                    batch_msg = f"**{len(new_entries)} nuevos códigos encontrados:**\n"
                    for entry in new_entries[:10]:
                        batch_msg += f"• [{entry.source}] {entry.title or entry.code[:40]}\n"
                    if len(new_entries) > 10:
                        batch_msg += f"... y {len(new_entries) - 10} más"
                    notifier.send("Nuevos códigos encontrados", batch_msg)
                except Exception as e:
                    logger.error(f"Batch notification failed: {e}")

        if _websocket_manager and new_entries:
            try:
                stats = {
                    "total": db.query(FoundCode).count(),
                    "new": db.query(FoundCode).filter(FoundCode.status == "new").count(),
                }
                _websocket_manager.broadcast({
                    "type": "new_codes",
                    "count": len(new_entries),
                    "stats": stats,
                })
            except Exception as e:
                logger.error(f"WebSocket broadcast failed: {e}")

        asf_cfg = db.query(ASFConfig).first() if (new_entries or db.query(FoundCode).filter(FoundCode.status == "new").limit(1).first()) else None

        if asf_cfg and asf_cfg.auto_redeem and asf_cfg.ipc_url:
            keys_to_redeem = [
                e for e in (new_entries or [])
                if e.code_type == "key"
                and e.validation_status == "valid"
                and not e.source.startswith("xbox/")
            ]
            existing_keys = [
                e for e in db.query(FoundCode).filter(
                    FoundCode.status == "new",
                    FoundCode.code_type == "key",
                    FoundCode.validation_status == "valid",
                ).all()
                if not e.source.startswith("xbox/")
            ]
            seen_ids = {e.id for e in keys_to_redeem}
            for e in existing_keys:
                if e.id not in seen_ids:
                    keys_to_redeem.append(e)
            if keys_to_redeem:
                from .asf_client import ASFClient
                asf = ASFClient(asf_cfg.ipc_url, asf_cfg.ipc_password)
                bots_to_try = [asf_cfg.default_bot, "secundaria1"]
                bots_to_try = list(dict.fromkeys(bots_to_try))
                DEMO_KEYWORDS = ("demo", "trial", "sample", "free weekend", "free access")
                for entry in keys_to_redeem:
                    try:
                        title_lower = (entry.title or "").lower()
                        if any(kw in title_lower for kw in DEMO_KEYWORDS):
                            logger.info(f"Key {entry.code} is demo/trial, skipping")
                            entry.status = "skipped"
                            entry.error_message = "Demo/trial"
                            db.commit()
                            continue
                        _redeem_key_on_bots(asf, entry.id, entry.code, bots_to_try, db)
                    except Exception as e:
                        logger.error(f"ASF redeem error for {entry.code}: {e}")

            free_games = [
                e for e in (new_entries or [])
                if e.code_type == "giveaway" and e.status == "new" and STEAM_APP_RE.search(e.code or e.source_url or "")
            ]
            existing_free = db.query(FoundCode).filter(
                FoundCode.status == "new",
                FoundCode.code_type == "giveaway",
            ).all()
            existing_free = [e for e in existing_free if STEAM_APP_RE.search(e.source_url or "")]
            seen_free = {e.id for e in free_games}
            for e in existing_free:
                if e.id not in seen_free:
                    free_games.append(e)
            if free_games:
                from .asf_client import ASFClient
                asf = ASFClient(asf_cfg.ipc_url, asf_cfg.ipc_password)
                bots_to_try = [asf_cfg.default_bot, "secundaria1"]
                bots_to_try = list(dict.fromkeys(bots_to_try))
                DEMO_KEYWORDS = ("demo", "trial", "sample", "free weekend", "free access")
                for entry in free_games:
                    try:
                        match = STEAM_APP_RE.search(entry.code or entry.source_url or "")
                        if not match:
                            continue
                        app_id = match.group(1)
                        title_lower = (entry.title or "").lower()
                        if any(kw in title_lower for kw in DEMO_KEYWORDS):
                            logger.info(f"App {app_id} is demo/trial, skipping")
                            entry.status = "skipped"
                            entry.error_message = "Demo/trial"
                            db.commit()
                            continue
                        sub_id = _get_free_sub(app_id)
                        if not sub_id:
                            logger.info(f"App {app_id} not free-to-keep, skipping")
                            entry.status = "skipped"
                            entry.error_message = "Not free-to-keep on Steam"
                            db.commit()
                            continue
                        sub_id = f"sub/{sub_id}"
                        _add_free_game_on_bots(asf, entry.id, app_id, sub_id, bots_to_try, db)
                    except Exception as e:
                        logger.error(f"Free game add error for {entry.code}: {e}")

        return new_entries
    except Exception as e:
        logger.error(f"Scraper run failed: {e}")
        db.rollback()
        return []
    finally:
        db.close()


def _redeem_key_on_bots(asf, entry_id, code, bots_to_try, db):
    db.commit()
    codes = [c.strip() for c in code.replace(",", " ").split()]
    redeemed_on_any = False
    already_on_any = False
    last_error = ""
    for key in codes:
        for bot in bots_to_try:
            result = asf.redeem_key(bot, key)
            if result.get("success"):
                redeemed_on_any = True
                logger.info(f"ASF redeemed: {key} on {bot}")
            else:
                msg = result.get("message", "")
                if "already" in msg.lower() or "duplicate" in msg.lower():
                    already_on_any = True
                    logger.info(f"ASF {key} already on {bot}")
                else:
                    last_error = msg
                    logger.warning(f"ASF failed: {key} on {bot} -> {msg}")
                    
    from .database import FoundCode
    entry = db.query(FoundCode).filter(FoundCode.id == entry_id).first()
    if entry:
        if redeemed_on_any or already_on_any:
            entry.status = "redeemed"
            entry.redeemed_at = datetime.now(timezone.utc)
            entry.error_message = None
        else:
            entry.status = "failed"
            entry.error_message = last_error
        db.commit()
    return redeemed_on_any or already_on_any


def _add_free_game_on_bots(asf, entry_id, app_id, sub_id, bots_to_try, db):
    db.commit()
    added_on_any = False
    already_on_any = False
    last_msg = ""
    for bot in bots_to_try:
        result = asf._do_request("POST", "/api/command", data={"command": f"addlicense {bot} {sub_id}"})
        msg = (result or {}).get("Result", "")
        if "OK" in msg:
            added_on_any = True
            logger.info(f"Free game added: app/{app_id} ({sub_id}) on {bot}")
        elif "Already" in msg:
            already_on_any = True
            logger.info(f"Free game app/{app_id} already on {bot}")
        else:
            last_msg = msg
            logger.warning(f"Free game failed app/{app_id} on {bot}: {msg}")
            
    from .database import FoundCode
    entry = db.query(FoundCode).filter(FoundCode.id == entry_id).first()
    if entry:
        if added_on_any or already_on_any:
            entry.status = "redeemed"
            entry.redeemed_at = datetime.now(timezone.utc)
            entry.error_message = None
        else:
            entry.status = "failed"
            entry.error_message = last_msg[:200]
        db.commit()
    return added_on_any or already_on_any

def start_scheduler():
    if scheduler.running:
        return

    from .database import SessionLocal, SearchSource
    from .scrapers.reddit import RedditScraper

    reddit_scraper = None

    def run_all_scrapers():
        run_scrapers_once(reddit_scraper=reddit_scraper)

    def init_reddit_scraper():
        nonlocal reddit_scraper
        db = SessionLocal()
        try:
            source = db.query(SearchSource).filter(SearchSource.name == "reddit").first()
            if source and source.config:
                cfg = source.config
                from .scrapers.reddit import RedditScraper
                reddit_scraper = RedditScraper(
                    cfg.get("client_id", ""),
                    cfg.get("client_secret", ""),
                    cfg.get("user_agent", "steam-hunter/1.0"),
                )
                logger.info("Reddit scraper initialized from config")
        except Exception as e:
            logger.warning(f"Reddit scraper not configured: {e}")
        finally:
            db.close()

    init_reddit_scraper()

    scheduler.add_job(
        run_all_scrapers,
        IntervalTrigger(minutes=15),
        id="scrape_all",
        replace_existing=True,
    )
    scheduler.add_job(
        init_reddit_scraper,
        IntervalTrigger(minutes=30),
        id="refresh_reddit",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_old_entries,
        IntervalTrigger(hours=24),
        id="cleanup_db",
        replace_existing=True,
    )

    scheduler.add_job(
        check_asf_health,
        IntervalTrigger(minutes=30),
        id="asf_health_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")


def check_asf_health():
    from .database import SessionLocal, ASFConfig, NotificationConfig as DBNotifConfig
    from .notifications import Notifier, NotificationConfig as NotifCfg
    from .asf_client import ASFClient

    db = SessionLocal()
    try:
        asf_cfg = db.query(ASFConfig).first()
        if not asf_cfg or not asf_cfg.ipc_url:
            return
        asf = ASFClient(asf_cfg.ipc_url, asf_cfg.ipc_password)
        bots = asf.get_bots()
        offline = [b for b in bots if not b.get("online")]
        if offline:
            names = ", ".join(b["name"] for b in offline)
            logger.warning(f"ASF bots offline: {names}")
            notif_cfg = db.query(DBNotifConfig).first()
            if notif_cfg and (notif_cfg.discord_webhook_url or notif_cfg.telegram_bot_token):
                notifier = Notifier(NotifCfg(
                    discord_webhook_url=notif_cfg.discord_webhook_url or "",
                    telegram_bot_token=notif_cfg.telegram_bot_token or "",
                    telegram_chat_id=notif_cfg.telegram_chat_id or "",
                ))
                notifier.send("🔴 Bots ASF desconectados", f"Los siguientes bots están offline: {names}")
    except Exception as e:
        logger.error(f"ASF health check failed: {e}")
    finally:
        db.close()


def cleanup_old_entries():
    from .database import SessionLocal, FoundCode

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        old = db.query(FoundCode).filter(
            FoundCode.found_at < cutoff,
            FoundCode.status.in_(["failed", "expired", "skipped", "redeemed"]),
        ).all()
        count = len(old)
        for entry in old:
            db.delete(entry)
        db.commit()
        if count:
            logger.info(f"Cleaned up {count} old entries (all statuses older than 30 days)")
    except Exception as e:
        logger.error(f"DB cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()
