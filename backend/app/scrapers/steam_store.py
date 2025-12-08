import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

STEAM_SPECIALS_URL = "https://store.steampowered.com/search/?specials=1&ndl=1"
STEAM_FREE_URL = "https://store.steampowered.com/genre/Free%20to%20Play/"

class SteamStoreScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://store.steampowered.com/",
        })

    def get_free_weekends(self) -> list[dict]:
        try:
            resp = self.session.get(
                "https://store.steampowered.com/search/?freeweekend=1&ndl=1",
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for row in soup.select("a.search_result_row"):
                title_el = row.select_one(".title")
                title = title_el.text.strip() if title_el else "Unknown"
                link = row.get("href", "")

                if "Free Weekend" in resp.text[:5000]:
                    results.append({
                        "source": "steam/free_weekend",
                        "source_url": link,
                        "title": f"Free Weekend: {title}",
                        "description": "",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping Steam free weekends: {e}")
            return []

    def get_permanent_free(self) -> list[dict]:
        try:
            resp = self.session.get(STEAM_FREE_URL, timeout=15)
            resp.raise_for_status()
            results = []

            steam_app_pattern = re.compile(r'https://store\.steampowered\.com/app/(\d+)')
            matches = steam_app_pattern.findall(resp.text)
            seen = set()

            for app_id in matches:
                if app_id not in seen:
                    seen.add(app_id)
                    results.append({
                        "source": "steam/free_to_play",
                        "source_url": f"https://store.steampowered.com/app/{app_id}",
                        "title": f"Free to Play: App {app_id}",
                        "description": "",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

            return results[:20]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping Steam free games: {e}")
            return []
