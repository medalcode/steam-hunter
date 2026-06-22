import logging
import random
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from ..constants import USER_AGENTS

logger = logging.getLogger(__name__)

STEAMGIFTS_GIVEAWAYS_URL = "https://www.steamgifts.com/giveaways/search?page={}"

class SteamGiftsScraper:
    def __init__(self, session_cookies: dict | None = None):
        self.session = requests.Session()
        self._set_headers()
        if session_cookies:
            for name, value in session_cookies.items():
                self.session.cookies.set(name, value)

    def _set_headers(self):
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.steamgifts.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def get_giveaways(self, pages: int = 2) -> list[dict]:
        results = []
        for page in range(1, pages + 1):
            try:
                self._set_headers()
                resp = self.session.get(STEAMGIFTS_GIVEAWAYS_URL.format(page), timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"SteamGifts page {page}: {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                for giveaway in soup.select(".giveaway__row-outer"):
                    link_el = giveaway.select_one("a.giveaway__link")
                    title_el = giveaway.select_one(".giveaway__title")
                    entries_el = giveaway.select_one(".giveaway__entries")

                    if not link_el or not title_el:
                        continue

                    title = title_el.text.strip()
                    link = f"https://www.steamgifts.com{link_el.get('href', '')}"
                    entries = entries_el.text.strip() if entries_el else "?"

                    results.append({
                        "source": "steamgifts",
                        "source_url": link,
                        "title": f"SG Giveaway: {title} ({entries})",
                        "description": f"Entries: {entries}",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

            except requests.RequestException as e:
                logger.error(f"Error scraping SteamGifts page {page}: {e}")

        return results
