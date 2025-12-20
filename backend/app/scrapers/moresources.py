import logging
import requests
import random
import json
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
]

HEADERS_TEMPLATE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class MoreSourcesScraper:
    def __init__(self):
        self.session = requests.Session()

    def _headers(self, referer: str = ""):
        h = {"User-Agent": random.choice(USER_AGENTS), **HEADERS_TEMPLATE}
        if referer:
            h["Referer"] = referer
        return h

    def _fetch(self, url: str, referer: str = "", **kwargs) -> requests.Response | None:
        for attempt in range(2):
            try:
                resp = self.session.get(url, headers=self._headers(referer), timeout=15, **kwargs)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"{url} -> {resp.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Fetch error {url}: {e}")
        return None

    def search_all(self) -> list[dict]:
        results = []
        results.extend(self._cheapshark_free())
        results.extend(self._reddit_more())
        results.extend(self._epic_freebies())
        results.extend(self._cheapshark_giveaways())
        results.extend(self._fanatical_free())
        return results

    def _cheapshark_free(self) -> list[dict]:
        try:
            resp = self._fetch(
                "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=0&pageSize=10",
                referer="https://www.cheapshark.com/",
            )
            if not resp:
                return []

            data = resp.json()
            results = []
            now = datetime.now(timezone.utc).isoformat()

            for deal in data[:10]:
                title = deal.get("title", "Unknown")
                deal_id = deal.get("dealID", "")
                steam_app = deal.get("steamAppID", "")
                sale_price = deal.get("salePrice", "0")

                if sale_price != "0.00":
                    continue

                link = f"https://www.cheapshark.com/redirect?dealID={deal_id}" if deal_id else ""
                steam_link = f"https://store.steampowered.com/app/{steam_app}" if steam_app else link

                results.append({
                    "source": "cheapshark/free",
                    "source_url": steam_link or link,
                    "title": f"Free: {title[:200]}",
                    "description": f"Price: ${sale_price}",
                    "found_at": now,
                })

            if results:
                logger.info(f"CheapShark free: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"CheapShark error: {e}")
            return []

    def _cheapshark_giveaways(self) -> list[dict]:
        try:
            resp = self._fetch(
                "https://www.cheapshark.com/api/1.0/deals?storeID=1&metacritic=80&pageSize=10&sortBy=Price&lowerPrice=0&upperPrice=1",
                referer="https://www.cheapshark.com/",
            )
            if not resp:
                return []

            data = resp.json()
            results = []
            now = datetime.now(timezone.utc).isoformat()

            for deal in data[:10]:
                title = deal.get("title", "Unknown")
                deal_id = deal.get("dealID", "")
                steam_app = deal.get("steamAppID", "")
                sale_price = deal.get("salePrice", "0")

                link = f"https://www.cheapshark.com/redirect?dealID={deal_id}" if deal_id else ""
                steam_link = f"https://store.steampowered.com/app/{steam_app}" if steam_app else link

                results.append({
                    "source": "cheapshark/deals",
                    "source_url": steam_link or link,
                    "title": f"Deal: {title[:200]} (${sale_price})",
                    "description": f"Price: ${sale_price} | Metacritic: {deal.get('metacriticScore', '?')}",
                    "found_at": now,
                })

            return results
        except Exception as e:
            logger.error(f"CheapShark deals error: {e}")
            return []

    def _reddit_more(self) -> list[dict]:
        subreddits = [
            ("r/FreeGamesOnSteam", "FreeGamesOnSteam"),
            ("r/FreeSteamGames", "FreeSteamGames"),
            ("r/GameDealsFree", "GameDealsFree"),
            ("r/FreeGameFindings", "FreeGameFindings"),
        ]

        results = []
        now = datetime.now(timezone.utc).isoformat()

        for label, sub in subreddits:
            try:
                resp = self._fetch(
                    f"https://www.reddit.com/r/{sub}/hot/.json?limit=10",
                    referer="https://www.reddit.com/",
                )
                if not resp:
                    continue

                data = resp.json()
                count = 0
                for post in data.get("data", {}).get("children", []):
                    p = post.get("data", {})
                    title = p.get("title", "")
                    url = p.get("url", "")
                    permalink = "https://www.reddit.com" + p.get("permalink", "")

                    keywords = ["free", "giveaway", "steam", "key", "100%", "claim", "grab"]
                    if not any(kw in title.lower() for kw in keywords):
                        continue

                    results.append({
                        "source": label,
                        "source_url": url if url.startswith("http") else permalink,
                        "title": f"{label}: {title[:200]}",
                        "description": "",
                        "found_at": now,
                    })
                    count += 1

                if count:
                    logger.info(f"{label}: {count} results")
            except Exception as e:
                logger.warning(f"{label} error: {e}")

        return results

    def _epic_freebies(self) -> list[dict]:
        try:
            now = datetime.now(timezone.utc).isoformat()
            results = []

            resp = self._fetch(
                "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US",
                referer="https://store.epicgames.com/",
            )
            if not resp:
                return []

            data = resp.json()
            catalog = data.get("data", {})
            if not catalog:
                catalog = data

            elements = catalog.get("Catalog", {}).get("searchStore", {}).get("elements", [])
            if not elements:
                elements = catalog.get("searchStore", {}).get("elements", [])

            for el in elements[:20]:
                title = el.get("title", "Unknown")
                product_slug = el.get("productSlug", el.get("urlSlug", ""))
                link = f"https://store.epicgames.com/en-US/p/{product_slug}" if product_slug else ""

                promotions = el.get("promotions", {}) or {}
                offers = promotions.get("promotionalOffers", []) or []
                if not offers:
                    offers = promotions.get("upcomingPromotionalOffers", []) or []

                is_free = False
                if offers:
                    for offer in offers:
                        promo_offers = offer.get("promotionalOffers", []) if offer else []
                        for o in promo_offers:
                            ds = o.get("discountSetting", {}) if o else {}
                            if ds.get("discountPercentage") == 0:
                                is_free = True

                if is_free and title:
                    results.append({
                        "source": "epic/free",
                        "source_url": link,
                        "title": f"Epic Free: {title[:200]}",
                        "description": "",
                        "found_at": now,
                    })

            if results:
                logger.info(f"Epic freebies: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Epic error: {e}")
            return []

    def _fanatical_free(self) -> list[dict]:
        try:
            resp = self._fetch(
                "https://www.fanatical.com/en/games?filter=Free&sort=name-asc",
                referer="https://www.fanatical.com/",
            )
            if not resp:
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            now = datetime.now(timezone.utc).isoformat()

            for link_el in soup.select("a[href*='/game/']")[:10]:
                title = link_el.get("title") or link_el.text.strip()
                href = link_el.get("href", "")
                if not title or not href:
                    continue
                if not href.startswith("http"):
                    href = "https://www.fanatical.com" + href

                results.append({
                    "source": "fanatical/free",
                    "source_url": href,
                    "title": f"Fanatical: {title[:200]}",
                    "description": "",
                    "found_at": now,
                })

            if results:
                logger.info(f"Fanatical free: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Fanatical error: {e}")
            return []
