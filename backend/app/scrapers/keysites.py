import logging
import requests
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
        "name": "steamcode.com",
        "url": "https://steamcode.com/",
        "selector": "article.post",
        "title_sel": "h2 a",
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
        for site in KEY_SITES:
            try:
                resp = self.session.get(site["url"], timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                for item in soup.select(site["selector"])[:10]:
                    title_el = item.select_one(site["title_sel"])
                    if not title_el:
                        continue

                    title = title_el.text.strip()
                    link = title_el.get("href", "")
                    if link and not link.startswith("http"):
                        domain = site["url"].rstrip("/")
                        link = domain + link

                    results.append({
                        "source": site["name"],
                        "source_url": link,
                        "title": title[:200],
                        "description": "",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

            except Exception as e:
                logger.error(f"Key site {site['name']} error: {e}")

        return results
