import logging
import re
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

STEAMGIFTS_GIVEAWAYS_URL = "https://www.steamgifts.com/giveaways/search?page={}"

class SteamGiftsScraper:
    def __init__(self, session_cookies: dict | None = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        if session_cookies:
            for name, value in session_cookies.items():
                self.session.cookies.set(name, value)

    def get_giveaways(self, pages: int = 2) -> list[dict]:
        results = []
        for page in range(1, pages + 1):
            try:
                resp = self.session.get(STEAMGIFTS_GIVEAWAYS_URL.format(page), timeout=15)
                resp.raise_for_status()
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
