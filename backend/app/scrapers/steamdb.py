import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

STEAMDB_FREE_URL = "https://steamdb.info/upcoming/free/"
STEAMDB_GIVEAWAYS_URL = "https://steamdb.info/giveaways/"

class SteamDBScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def get_free_promotions(self) -> list[dict]:
        try:
            resp = self.session.get(STEAMDB_FREE_URL, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            table = soup.select_one("table.table")
            if not table:
                logger.warning("No free promotions table found on SteamDB")
                return results

            for row in table.select("tbody tr"):
                cols = row.select("td")
                if len(cols) < 3:
                    continue

                app_link = row.select_one("a")
                title = app_link.text.strip() if app_link else "Unknown"
                app_url = f"https://steamdb.info{app_link['href']}" if app_link and app_link.get("href") else ""

                results.append({
                    "source": "steamdb/free",
                    "source_url": app_url,
                    "title": f"Free promotion: {title}",
                    "description": "",
                    "found_at": datetime.now(timezone.utc).isoformat(),
                })

            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping SteamDB free: {e}")
            return []

    def get_giveaways(self) -> list[dict]:
        try:
            resp = self.session.get(STEAMDB_GIVEAWAYS_URL, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            table = soup.select_one("table.table")
            if not table:
                return results

            for row in table.select("tbody tr"):
                app_link = row.select_one("a")
                if not app_link:
                    continue

                title = app_link.text.strip()
                app_url = f"https://steamdb.info{app_link['href']}" if app_link.get("href") else ""

                results.append({
                    "source": "steamdb/giveaway",
                    "source_url": app_url,
                    "title": f"Giveaway: {title}",
                    "description": "",
                    "found_at": datetime.now(timezone.utc).isoformat(),
                })

            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping SteamDB giveaways: {e}")
            return []
