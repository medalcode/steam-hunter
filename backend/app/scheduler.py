import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)

def start_scheduler():
    if scheduler.running:
        return

    from .database import SessionLocal, FoundCode, SearchSource
    from .parser import parse_all
    from .scrapers.reddit import RedditScraper
    from .scrapers.steamdb import SteamDBScraper
    from .scrapers.steam_store import SteamStoreScraper

    reddit_scraper = None
    steamdb_scraper = SteamDBScraper()
    steam_scraper = SteamStoreScraper()

    def run_all_scrapers():
        db = SessionLocal()
        try:
            all_results = []

            if reddit_scraper:
                try:
                    all_results.extend(reddit_scraper.search_recent())
                except Exception as e:
                    logger.error(f"Reddit scrape failed: {e}")

            try:
                all_results.extend(steamdb_scraper.get_free_promotions())
            except Exception as e:
                logger.error(f"SteamDB free scrape failed: {e}")

            try:
                all_results.extend(steamdb_scraper.get_giveaways())
            except Exception as e:
                logger.error(f"SteamDB giveaway scrape failed: {e}")

            try:
                all_results.extend(steam_scraper.get_free_weekends())
            except Exception as e:
                logger.error(f"Steam weekend scrape failed: {e}")

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
                    code_type = "key" if "-" in code and len(code) > 10 else "gift_link" if "gift" in code or "friend" in code else "giveaway"
                    entry = FoundCode(
                        code=code,
                        code_type=code_type,
                        source=result["source"],
                        source_url=result.get("source_url"),
                        title=result.get("title"),
                        description=result.get("description"),
                        status="new",
                    )
                    db.add(entry)

                db.commit()

        except Exception as e:
            logger.error(f"Scraper run failed: {e}")
            db.rollback()
        finally:
            db.close()

    def init_reddit_scraper(config: dict):
        nonlocal reddit_scraper
        client_id = config.get("reddit_client_id")
        client_secret = config.get("reddit_client_secret")
        user_agent = config.get("reddit_user_agent", "steam-hunter/1.0")

        if client_id and client_secret:
            reddit_scraper = RedditScraper(client_id, client_secret, user_agent)
            logger.info("Reddit scraper initialized")

    scheduler.add_job(
        run_all_scrapers,
        IntervalTrigger(minutes=15),
        id="scrape_all",
        replace_existing=True,
    )

    logger.info("Scheduler started")
