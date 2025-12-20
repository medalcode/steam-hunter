import logging
import requests
import random
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
]

BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "TE": "trailers",
}

class KeySitesScraper:
    def __init__(self):
        self.session = requests.Session()
        self._set_headers()

    def _set_headers(self, referer: str = ""):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            **BROWSER_HEADERS,
        }
        if referer:
            headers["Referer"] = referer
        self.session.headers.update(headers)

    def _fetch(self, url: str, referer: str = "", max_retries: int = 2, **kwargs) -> requests.Response | None:
        for attempt in range(max_retries):
            try:
                self._set_headers(referer=referer)
                resp = self.session.get(url, timeout=15, **kwargs)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"{url} -> {resp.status_code}, attempt {attempt + 1}")
                if resp.status_code == 403 and attempt == 0:
                    self.session.cookies.clear()
                    self.session.get(url, timeout=10)
            except requests.RequestException as e:
                logger.warning(f"Request error {url}: {e}")
        return None

    def search_all(self) -> list[dict]:
        results = []
        results.extend(self._scrape_gamerpower())
        results.extend(self._scrape_configured_sites())
        results.extend(self._scrape_giveaway_su())
        results.extend(self._scrape_steam_giveaway_steam())
        results.extend(self._scrape_reddit_fallback())
        return results

    def _scrape_gamerpower(self) -> list[dict]:
        try:
            self._set_headers(referer="https://www.gamerpower.com/")
            resp = self._fetch(
                "https://www.gamerpower.com/giveaways/steam/free-games",
                referer="https://www.gamerpower.com/",
            )
            if not resp:
                logger.error("GamerPower: no response")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for item in soup.select(".giveaway-item, .card, .game-item")[:30]:
                link_el = item.select_one("a[href*='gamerpower']") or item.select_one("a")
                title_el = item.select_one(".giveaway-title, .card-title, h3, h2")

                if not title_el:
                    continue

                title = title_el.text.strip()
                link = ""
                if link_el and link_el.get("href"):
                    link = link_el["href"]
                    if not link.startswith("http"):
                        link = "https://www.gamerpower.com" + link

                if not title:
                    continue

                results.append({
                    "source": "gamerpower",
                    "source_url": link,
                    "title": f"GP: {title[:200]}",
                    "description": "",
                    "found_at": datetime.now(timezone.utc).isoformat(),
                })

            logger.info(f"GamerPower: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"GamerPower error: {e}")
            return []

    def _scrape_configured_sites(self) -> list[dict]:
        results = []

        for site in [
            {
                "name": "freesteamkeys.com",
                "url": "https://www.freesteamkeys.com/",
                "selector": "article, .giveaway-item, .game-item",
                "title_sel": "a[href*='giveaway'], h2 a, h3 a, article a",
            },
            {
                "name": "indiegamebundles",
                "url": "https://www.indiegamebundles.com/free-games/",
                "selector": ".entry-content a, .post-content a",
                "title_sel": None,
            },
            {
                "name": "indiegala",
                "url": "https://freebies.indiegala.com/",
                "selector": ".card, .free-item, .game-card",
                "title_sel": ".card-title a, .free-item a, .game-card a",
            },
        ]:
            try:
                self._set_headers(referer=site["url"])
                resp = self._fetch(site["url"], referer=site["url"])
                if not resp:
                    logger.warning(f"{site['name']}: no response, trying fallback")
                    results.extend(self._ggdeals_fallback())
                    continue

                soup = BeautifulSoup(resp.text, "lxml")
                items = soup.select(site["selector"])[:10]

                for item in items:
                    title = ""
                    link = ""

                    if site["title_sel"]:
                        title_el = item.select_one(site["title_sel"])
                        if title_el:
                            title = title_el.text.strip()
                            link = title_el.get("href", "")
                    else:
                        title = item.text.strip()
                        link = item.get("href", "")

                    if not title:
                        continue

                    if link and not link.startswith("http"):
                        domain = site["url"].rstrip("/")
                        link = domain + link

                    if not any(kw in title.lower() for kw in ["steam", "key", "free", "giveaway"]):
                        continue

                    results.append({
                        "source": site["name"],
                        "source_url": link,
                        "title": title[:200],
                        "description": "",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

                logger.info(f"{site['name']}: {len(items)} items")
            except Exception as e:
                logger.error(f"Key site {site['name']} error: {e}")

        return results

    def _ggdeals_fallback(self) -> list[dict]:
        try:
            self._set_headers(referer="https://gg.deals/")
            resp = self._fetch(
                "https://gg.deals/giveaways/",
                referer="https://gg.deals/",
            )
            if not resp:
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for title_el in soup.select("a[href*='/giveaway/'], .giveaway-item__title a")[:15]:
                title = title_el.text.strip()
                link = title_el.get("href", "")
                if not title:
                    continue
                if link and not link.startswith("http"):
                    link = "https://gg.deals" + link
                results.append({
                    "source": "gg.deals",
                    "source_url": link,
                    "title": f"GG: {title[:200]}",
                    "description": "",
                    "found_at": datetime.now(timezone.utc).isoformat(),
                })

            logger.info(f"GG.deals: {len(results)} results (fallback)")
            return results
        except Exception as e:
            logger.error(f"GG.deals fallback error: {e}")
            return []

    def _scrape_giveaway_su(self) -> list[dict]:
        try:
            self._set_headers(referer="https://giveaway.su/")
            resp = self._fetch("https://giveaway.su/", referer="https://giveaway.su/")
            if not resp:
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for link_el in soup.select("a[href*='giveaway'], a[href*='/game/']")[:20]:
                title = link_el.text.strip()
                link = link_el.get("href", "")
                if not title or len(title) < 3:
                    continue
                if link and not link.startswith("http"):
                    link = "https://giveaway.su" + link

                results.append({
                    "source": "giveaway.su",
                    "source_url": link,
                    "title": f"GA: {title[:200]}",
                    "description": "",
                    "found_at": datetime.now(timezone.utc).isoformat(),
                })

            logger.info(f"GiveAway.su: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"GiveAway.su error: {e}")
            return []

    def _scrape_steam_giveaway_steam(self) -> list[dict]:
        try:
            self._set_headers(referer="https://store.steampowered.com/")
            resp = self._fetch(
                "https://store.steampowered.com/search/?specials=1&ndl=1",
                referer="https://store.steampowered.com/",
            )
            if not resp:
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            now = datetime.now(timezone.utc).isoformat()

            for row in soup.select("a.search_result_row")[:20]:
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
                logger.info(f"Steam specials: {len(results)} free games found")
            return results
        except Exception as e:
            logger.error(f"Steam specials error: {e}")
            return []

    def _scrape_reddit_fallback(self) -> list[dict]:
        sources = [
            ("r/FreeGameFindings", "https://www.reddit.com/r/FreeGameFindings/hot/.json?limit=15"),
            ("r/GameDeals", "https://www.reddit.com/r/GameDeals/hot/.json?limit=10"),
        ]
        results = []
        now = datetime.now(timezone.utc).isoformat()

        for name, url in sources:
            try:
                self._set_headers(referer="https://www.reddit.com/")
                resp = self._fetch(url, referer="https://www.reddit.com/")
                if not resp:
                    continue

                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    p = post.get("data", {})
                    title = p.get("title", "")
                    link = p.get("url", "")
                    permalink = "https://www.reddit.com" + p.get("permalink", "")

                    keywords = ["free", "giveaway", "steam", "key", "100%"]
                    if not any(kw in title.lower() for kw in keywords):
                        continue

                    results.append({
                        "source": name,
                        "source_url": link if link.startswith("http") else permalink,
                        "title": f"{name}: {title[:200]}",
                        "description": "",
                        "found_at": now,
                    })

                logger.info(f"{name}: {len(results)} fallback items")
            except Exception as e:
                logger.warning(f"Reddit {name} error: {e}")

        return results
