import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

BROWSE_API = "https://emerald.xboxservices.com/xboxcomfd/browse"
PAGES_TO_SCAN = int(os.environ.get("XBOX_CATALOG_PAGES", "15"))
DELAY = 0.3

XBOX_COOKIES_FILE = "xbox_cookies.json"


def _get_cookies() -> dict | None:
    raw = os.environ.get("XBOX_COOKIES", "")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    filepath = os.environ.get("XBOX_COOKIES_FILE", XBOX_COOKIES_FILE)
    if filepath:
        try:
            with open(filepath) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return None


class XboxCatalogScraper:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = _get_cookies()

    def search_freebies(self) -> list[dict]:
        if not self.cookies:
            logger.warning("XBOX_COOKIES not set — cannot scrape Xbox catalog")
            return []

        now = datetime.now(timezone.utc).isoformat()
        results = []
        seen_ids = set()

        for page in range(1, PAGES_TO_SCAN + 1):
            try:
                resp = self.session.get(
                    BROWSE_API,
                    params={
                        "locale": "en-US",
                        "pageNumber": page,
                        "resultsPerPage": 50,
                    },
                    cookies=self.cookies,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                        "MS-CV": str(uuid.uuid4()).replace("-", "") + ".0",
                        "Referer": "https://www.xbox.com/",
                    },
                    timeout=20,
                )
                if resp.status_code != 200:
                    logger.warning(f"Browse API page {page}: {resp.status_code}")
                    break

                data = resp.json()
                availabilities = self._normalize_avails(data)

                for a in availabilities:
                    pid = a.get("productId", "")
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    is_free, price_info = self._is_free(a)
                    if not is_free:
                        continue

                    p = self._find_product(data, pid)
                    title = (p or {}).get("title", pid) or pid
                    categories = (p or {}).get("categories", [])

                    if self._is_demo(title, categories):
                        continue

                    slug = self._make_slug(title)
                    results.append({
                        "source": "xbox/free",
                        "source_url": f"https://www.xbox.com/en-US/games/store/{slug}/{pid}",
                        "title": f"Xbox Free: {title[:200]}",
                        "description": (
                            f"Categories: {', '.join(categories[:5])}"
                            if categories
                            else f"Xbox free game"
                        ),
                        "found_at": now,
                    })

                time.sleep(DELAY)

            except requests.RequestException as e:
                logger.error(f"Browse API page {page}: {e}")
                break

        if results:
            logger.info(f"Xbox Catalog: {len(results)} free games (scanned {PAGES_TO_SCAN} pages)")
        else:
            logger.info("Xbox Catalog: no free games found")

        return results

    def _normalize_avails(self, data: dict) -> list[dict]:
        raw = data.get("availabilitySummaries", [])
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            out = []
            for pid, skus in raw.items():
                if isinstance(skus, dict):
                    for sku, aids in skus.items():
                        if isinstance(aids, dict):
                            for aid, entry in aids.items():
                                entry["productId"] = pid
                                entry["skuId"] = sku
                                out.append(entry)
            return out
        return []

    def _find_product(self, data: dict, pid: str) -> dict | None:
        prods = data.get("productSummaries", [])
        if isinstance(prods, list):
            for p in prods:
                if p.get("productId") == pid:
                    return p
        if isinstance(prods, dict):
            return prods.get(pid)
        return None

    def _is_free(self, availability: dict) -> tuple[bool, dict | None]:
        price = availability.get("price") or {}
        lp = price.get("listPrice")
        if lp is not None and lp == 0:
            return True, price
        return False, None

    def _is_demo(self, title: str, categories: list[str]) -> bool:
        lower = title.lower()
        if "demo" in lower or "trial" in lower or "showcase" in lower:
            return True
        if any("demo" in (c or "").lower() for c in categories):
            return True
        return False

    def _make_slug(self, title: str) -> str:
        slug = title.lower()
        for ch in "®™©'.,:!?()[]":
            slug = slug.replace(ch, "")
        slug = "-".join(slug.split())
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug.strip("-")
