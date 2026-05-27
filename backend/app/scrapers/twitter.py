import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.lqdev.tech",
    "https://nitter.space",
]

TWITTER_ACCOUNTS = [
    "FreeGameFindings",
    "SteamDeals",
    "giveaway_steam",
    "Steam_Giveaways",
]

class TwitterScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })

    def search_giveaways(self) -> list[dict]:
        results = []
        for account in TWITTER_ACCOUNTS:
            for instance in NITTER_INSTANCES:
                try:
                    posts = self._scrape_account(instance, account)
                    if posts is not None:
                        results.extend(posts)
                        break
                except requests.RequestException:
                    continue
        return results

    def _scrape_account(self, instance: str, account: str) -> list[dict] | None:
        try:
            resp = self.session.get(
                f"{instance}/{account}",
                timeout=15,
                headers={"Accept": "text/html"},
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for tweet in soup.select(".timeline-item")[:10]:
                content_el = tweet.select_one(".tweet-content")
                if not content_el:
                    continue

                text = content_el.text.strip()
                link_el = tweet.select_one("a.tweet-link")
                tweet_url = ""
                if link_el and link_el.get("href"):
                    tweet_url = f"https://twitter.com{link_el['href']}"

                giveaway_keywords = [
                    "free", "giveaway", "key", "steam", "code",
                    "gratis", "regalo", "sorteo",
                ]
                if any(kw in text.lower() for kw in giveaway_keywords):
                    results.append({
                        "source": f"twitter/{account}",
                        "source_url": tweet_url,
                        "title": text[:200],
                        "description": text[:2000],
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

            return results
        except requests.RequestException as e:
            logger.debug(f"Nitter {instance}/{account} failed: {e}")
            return None
