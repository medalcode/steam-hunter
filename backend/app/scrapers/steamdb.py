import logging
import random
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import cloudscraper

logger = logging.getLogger(__name__)

STEAMDB_FREE_URL = "https://steamdb.info/upcoming/free/"
STEAMDB_GIVEAWAYS_URL = "https://steamdb.info/giveaways/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
]

class SteamDBScraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False,
                "desktop": True,
            },
        )
        self._set_headers()

    def _set_headers(self):
        self.scraper.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://steamdb.info/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

    def _fetch(self, url: str) -> str | None:
        for attempt in range(3):
            try:
                self._set_headers()
                resp = self.scraper.get(url, timeout=20)
                if resp.status_code == 200:
                    return resp.text
                logger.warning(f"SteamDB {url} -> {resp.status_code}, attempt {attempt + 1}")
                if attempt == 0:
                    self.scraper.get("https://steamdb.info/", timeout=10)
                elif attempt == 1:
                    api_url = url.replace("steamdb.info/upcoming/free/", "steamdb.info/api/upcoming/free/")
                    api_url = api_url.replace("steamdb.info/giveaways/", "steamdb.info/api/giveaways/")
                    if api_url != url:
                        resp = self.scraper.get(api_url, timeout=20)
                        if resp.status_code == 200:
                            return resp.text
            except Exception as e:
                logger.warning(f"SteamDB fetch error: {e}")
        return None

    def _fallback_charts(self) -> list[dict]:
        try:
            r = requests.get(
                "https://store.steampowered.com/search/?specials=1&ndl=1",
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=10,
            )
            if r.status_code != 200:
                logger.warning(f"Steam store fallback: {r.status_code}")
                return []

            results = []
            now = datetime.now(timezone.utc).isoformat()
            soup = BeautifulSoup(r.text, "lxml")
            for row in soup.select("a.search_result_row")[:15]:
                title_el = row.select_one(".title")
                title = title_el.text.strip() if title_el else "Unknown"
                link = row.get("href", "")
                discount_el = row.select_one(".discount_pct")
                if discount_el and discount_el.text.strip() == "-100%":
                    results.append({
                        "source": "steam/specials",
                        "source_url": link,
                        "title": f"Free: {title}",
                        "description": "",
                        "found_at": now,
                    })
            if results:
                logger.info(f"Steam store fallback: {len(results)} free games")
            else:
                logger.info("Steam store fallback: no 100% discounts found")
            return results
        except Exception as e:
            logger.error(f"Fallback charts error: {e}")
            return []

    def _parse_apps(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        now = datetime.now(timezone.utc).isoformat()

        for table in soup.select("table"):
            rows = table.select("tbody tr") if table.select("tbody") else table.select("tr")
            for row in rows:
                link_el = row.select_one("a")
                if not link_el:
                    continue
                title = link_el.get("title") or link_el.text.strip()
                href = link_el.get("href", "")
                if not title or not href:
                    continue
                if href.startswith("/"):
                    href = "https://steamdb.info" + href
                if title:
                    results.append({
                        "source": "steamdb",
                        "source_url": href,
                        "title": title[:200],
                        "description": "",
                        "found_at": now,
                    })
        return results

    def get_free_promotions(self) -> list[dict]:
        html = self._fetch(STEAMDB_FREE_URL)
        if not html:
            return self._fallback_charts()
        items = self._parse_apps(html)
        for i in items:
            i["title"] = f"Free: {i['title']}"
        logger.info(f"SteamDB Free: {len(items)} results")
        return items

    def get_giveaways(self) -> list[dict]:
        html = self._fetch(STEAMDB_GIVEAWAYS_URL)
        if not html:
            return []
        items = self._parse_apps(html)
        for i in items:
            i["title"] = f"Giveaway: {i['title']}"
        logger.info(f"SteamDB Giveaways: {len(items)} results")
        return items
