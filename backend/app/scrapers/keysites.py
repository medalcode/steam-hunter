import logging
import requests
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KEY_SITES = [
    {
        "name": "gg.deals",
        "url": "https://gg.deals/giveaways/",
        "selector": ".giveaway-item",
        "title_sel": ".giveaway-item__title a",
    },
    {
        "name": "freesteamkeys.com",
        "url": "https://www.freesteamkeys.com/",
        "selector": ".giveaway-item, article, .game-item",
        "title_sel": "a[href*='giveaway'], h2 a, h3 a",
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
]

class KeySitesScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def search_all(self) -> list[dict]:
        results = []
        results.extend(self._scrape_gamerpower())
        results.extend(self._scrape_configured_sites())
        results.extend(self._scrape_giveaway_su())
        return results

    def _scrape_gamerpower(self) -> list[dict]:
        try:
            resp = self.session.get(
                "https://www.gamerpower.com/giveaways/steam/free-games",
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for item in soup.select(".giveaway-item, .card, .game-item")[:20]:
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
        for site in KEY_SITES:
            try:
                resp = self.session.get(site["url"], timeout=15)
                resp.raise_for_status()
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
                        title_el = item
                        title = title_el.text.strip()
                        link = title_el.get("href", "")

                    if not title:
                        continue

                    if link and not link.startswith("http"):
                        domain = site["url"].rstrip("/")
                        link = domain + link

                    steam_keywords = ["steam", "key", "free", "giveaway"]
                    if not any(kw in title.lower() for kw in steam_keywords):
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

    def _scrape_giveaway_su(self) -> list[dict]:
        try:
            resp = self.session.get("https://giveaway.su/", timeout=15)
            resp.raise_for_status()
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
