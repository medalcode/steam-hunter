import logging
import requests
import random
import re
import json
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

STEAM_SPECIALS_URL = "https://store.steampowered.com/search/?specials=1&ndl=1"
STEAM_FREE_URL = "https://store.steampowered.com/genre/Free%20to%20Play/"
STEAM_FREE_WEEKEND = "https://store.steampowered.com/search/?freeweekend=1&ndl=1"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
]

class SteamStoreScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.cookies.set("SteamLanguage", "english")
        self.session.cookies.set("birthtime", "757302001")
        self.session.cookies.set("lasters_check", "1")

    def _headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://store.steampowered.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _fetch(self, url: str) -> requests.Response | None:
        for attempt in range(2):
            try:
                resp = self.session.get(url, headers=self._headers(), timeout=20)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"Steam {url} -> {resp.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Steam fetch error: {e}")
        return None

    def search_freebies(self) -> list[dict]:
        """All-in-one: temporary free games + free weekends + F2P"""
        results = []
        results.extend(self._temp_free_games())
        results.extend(self.get_free_weekends())
        return results

    def _temp_free_games(self) -> list[dict]:
        """Games that are temporarily 100% off (not F2P)"""
        urls = [
            STEAM_SPECIALS_URL,
            "https://store.steampowered.com/search/?specials=1&ndl=1&sort_by=Price_ASC&maxprice=0",
            "https://store.steampowered.com/search/?term=&specials=1&category1=998%2C21%2C22%2C29%2C30%2C31%2C32%2C33%2C34%2C35%2C37%2C38%2C39%2C40%2C41%2C42%2C44%2C45%2C46%2C47%2C48%2C49%2C50%2C51%2C52%2C53%2C54%2C55%2C56%2C57%2C58%2C59%2C60%2C61%2C62%2C63%2C64%2C65%2C66%2C67%2C68%2C69%2C70%2C71%2C72%2C73%2C74%2C75%2C76%2C77%2C78%2C79%2C80%2C81%2C82%2C83%2C84%2C85%2C86%2C87%2C88%2C89%2C90%2C91%2C92%2C93%2C94%2C95%2C96%2C97%2C98%2C99%2C100&page=1",
        ]

        seen_urls = set()
        results = []
        now = datetime.now(timezone.utc).isoformat()

        for url in urls:
            resp = self._fetch(url)
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            rows = soup.select("a.search_result_row")

            for row in rows:
                link = row.get("href", "")
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                title_el = row.select_one(".title")
                title = title_el.text.strip() if title_el else ""

                discount_pct = ""
                pct_el = row.select_one(".discount_pct")
                if pct_el:
                    discount_pct = pct_el.text.strip()

                original_price = ""
                orig_el = row.select_one(".discount_original_price")
                if orig_el:
                    original_price = orig_el.text.strip()

                final_price = ""
                final_el = row.select_one(".discount_final_price")
                if final_el:
                    final_price = final_el.text.strip()

                if discount_pct != "-100%":
                    continue

                has_original_price = bool(original_price) and original_price != "Free to Play"
                if not has_original_price:
                    continue

                results.append({
                    "source": "steam/temp_free",
                    "source_url": link,
                    "title": f"TEMP FREE: {title[:200]}",
                    "description": f"Was: {original_price} | Discount: {discount_pct}",
                    "found_at": now,
                })

            if results:
                break

        if results:
            logger.info(f"Steam temp free: {len(results)} games found")
        else:
            logger.info("Steam temp free: no -100% discounts found right now")
        return results

    def get_free_weekends(self) -> list[dict]:
        resp = self._fetch(STEAM_FREE_WEEKEND)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        now = datetime.now(timezone.utc).isoformat()

        for row in soup.select("a.search_result_row"):
            title_el = row.select_one(".title")
            title = title_el.text.strip() if title_el else "Unknown"
            link = row.get("href", "")

            results.append({
                "source": "steam/free_weekend",
                "source_url": link,
                "title": f"Free Weekend: {title}",
                "description": "",
                "found_at": now,
            })

        if results:
            logger.info(f"Steam free weekend: {len(results)} games")
        return results

    def get_permanent_free(self) -> list[dict]:
        resp = self._fetch(STEAM_FREE_URL)
        if not resp:
            return []

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

        if results:
            logger.info(f"Steam F2P: {len(results)} games")
        return results[:20]
