import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

CATALOG_API = "https://catalog.gog.com/v1/catalog"
PAGES = 25
DELAY = 0.3

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.gog.com/",
}


class GOGScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def search_freebies(self) -> list[dict]:
        results = []
        seen = set()
        now = datetime.now(timezone.utc).isoformat()

        for page in range(1, PAGES + 1):
            try:
                resp = self.session.get(
                    CATALOG_API,
                    params={
                        "limit": 48,
                        "price": "between:0,0",
                        "productType": "in:game",
                        "page": page,
                        "countryCode": "US",
                        "locale": "en-US",
                        "currencyCode": "USD",
                    },
                    timeout=20,
                )
                if resp.status_code != 200:
                    logger.warning(f"GOG catalog page {page}: {resp.status_code}")
                    break

                data = resp.json()
                products = data.get("products", [])
                if not products:
                    break

                for p in products:
                    title = p.get("title", "")
                    slug = p.get("slug", "")
                    store_link = p.get("storeLink", "") or f"https://www.gog.com/en/game/{slug}"
                    fm = p.get("price", {}).get("finalMoney", {})

                    if fm.get("amount") not in ("0.00", "0"):
                        continue
                    if not title or title in seen:
                        continue
                    if "demo" in title.lower():
                        continue

                    seen.add(title)
                    results.append({
                        "source": "gog/free",
                        "source_url": store_link,
                        "title": f"GOG: {title[:200]}",
                        "description": f"Free game on GOG",
                        "found_at": now,
                    })

                total = data.get("productCount", 0)
                if page * 48 >= total:
                    break

                time.sleep(DELAY)

            except requests.RequestException as e:
                logger.error(f"GOG catalog page {page}: {e}")
                break

        if results:
            logger.info(f"GOG: {len(results)} free games (scanned {page} pages)")
        else:
            logger.info("GOG: no free games found")

        return results
