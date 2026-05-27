import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

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

def start_scheduler():
    if scheduler.running:
        return

    from .database import SessionLocal, FoundCode, SearchSource, SteamAccount
    from .parser import parse_all
    from .scrapers.reddit import RedditScraper
    from .scrapers.steamdb import SteamDBScraper
    from .scrapers.steam_store import SteamStoreScraper
    from .scrapers.steamgifts import SteamGiftsScraper
    from .scrapers.twitter import TwitterScraper
    from .scrapers.telegram_scraper import TelegramScraper
    from .scrapers.keysites import KeySitesScraper
    from .notifications import Notifier, NotificationConfig as NotifCfg

    reddit_scraper = None
    twitter_scraper = TwitterScraper()
    steamdb_scraper = SteamDBScraper()
    steam_scraper = SteamStoreScraper()
    steamgifts_scraper = SteamGiftsScraper()
    telegram_scraper = TelegramScraper()
    keysites_scraper = KeySitesScraper()

    def run_all_scrapers():
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
                ("Reddit", lambda: reddit_scraper.search_recent() if reddit_scraper else []),
                ("SteamDB Free", steamdb_scraper.get_free_promotions),
                ("SteamDB Giveaways", steamdb_scraper.get_giveaways),
                ("Steam Free Weekend", steam_scraper.get_free_weekends),
                ("SteamGifts", steamgifts_scraper.get_giveaways),
                ("Twitter", twitter_scraper.search_giveaways),
                ("Telegram", telegram_scraper.search_channels),
                ("Key Sites", keysites_scraper.search_all),
            ]

            for name, scrape_fn in scrapers_config:
                try:
                    results = scrape_fn()
                    all_results.extend(results)
                    logger.info(f"{name}: {len(results)} results")
                except Exception as e:
                    logger.error(f"{name} scrape failed: {e}")

            new_entries = []
            for result in all_results:
                parsed = parse_all(result.get("title", "") + " " + result.get("description", ""))
                if not parsed["keys"] and not parsed["gift_links"] and not parsed["giveaway_links"]:
                    continue

                existing = db.query(FoundCode).filter(
                    FoundCode.source_url == result["source_url"],
                    FoundCode.status != "expired",
                ).first()
                if existing:
                    continue

                all_codes = parsed["keys"] + parsed["gift_links"] + parsed["giveaway_links"]
                for code in all_codes:
                    code_type = (
                        "key" if "-" in code and len(code) > 10
                        else "gift_link" if "gift" in code or "friend" in code
                        else "giveaway"
                    )

                    from .validator import validate_key_format, validate_gift_link
                    validation = {"valid": True, "reason": ""}
                    if code_type == "key":
                        validation = validate_key_format(code)
                    elif code_type == "gift_link":
                        validation = validate_gift_link(code)

                    entry = FoundCode(
                        code=code,
                        code_type=code_type,
                        source=result["source"],
                        source_url=result.get("source_url"),
                        title=result.get("title"),
                        description=result.get("description"),
                        status="new",
                        validation_status="valid" if validation["valid"] else "invalid",
                        validation_reason=validation["reason"][:500],
                    )
                    db.add(entry)
                    new_entries.append(entry)

                db.commit()

                for entry in new_entries:
                    try:
                        notifier.send_code_found(
                            code_value=entry.code,
                            code_type=entry.code_type,
                            source=entry.source,
                            title=entry.title or "",
                            url=entry.source_url or "",
                        )
                    except Exception as e:
                        logger.error(f"Notification failed: {e}")

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

        except Exception as e:
            logger.error(f"Scraper run failed: {e}")
            db.rollback()
        finally:
            db.close()

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

    logger.info("Scheduler started")
