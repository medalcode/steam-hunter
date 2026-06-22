import logging
import re
import json
import requests
import random
from datetime import datetime, timezone

from ..constants import USER_AGENTS

logger = logging.getLogger(__name__)

PRELOADED_RE = re.compile(r"__PRELOADED_STATE__\s*=\s*({.*?});")

class XboxScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    def _fetch_preloaded(self, url: str) -> dict | None:
        try:
            resp = self.session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.warning(f"Xbox {url[:80]} -> {resp.status_code}")
                return None
            m = PRELOADED_RE.search(resp.text)
            if not m:
                logger.warning("Xbox: no __PRELOADED_STATE__ found")
                return None
            return json.loads(m.group(1))
        except Exception as e:
            logger.error(f"Xbox fetch error: {e}")
            return None

    def _extract_free_games(self, state: dict) -> list[dict]:
        prods = state.get("core2", {}).get("products", {})
        summaries = prods.get("productSummaries", {})
        availability = prods.get("availabilitySummaries", {})
        now = datetime.now(timezone.utc).isoformat()
        results = []

        for pid in summaries:
            summary = summaries[pid]
            if summary.get("productKind") != "Game" or summary.get("productFamily") != "Games":
                continue

            avails_for_pid = availability.get(pid, {})
            is_free = False
            for sku in avails_for_pid:
                for aid in avails_for_pid[sku]:
                    entry = avails_for_pid[sku][aid]
                    price_info = entry.get("price", {})
                    if price_info.get("listPrice") == 0:
                        is_free = True
                        break
                if is_free:
                    break

            if not is_free:
                continue

            title = summary.get("title", "")
            if not title:
                title = pid

            categories = summary.get("categories", [])
            xbox_url = f"https://www.xbox.com/en-US/games/store/-/{pid}"

            results.append({
                "source": "xbox/free",
                "source_url": xbox_url,
                "title": f"Xbox Free: {title[:200]}",
                "description": f"Categories: {', '.join(categories[:5])}" if categories else f"Xbox free game",
                "found_at": now,
            })

        return results

    def search_freebies(self) -> list[dict]:
        seen = set()
        results = []

        for url in [
            "https://www.xbox.com/en-US/games/browse?price=Free",
            "https://www.xbox.com/en-US/search/results?q=free&category=games",
        ]:
            state = self._fetch_preloaded(url)
            if not state:
                continue
            games = self._extract_free_games(state)
            for g in games:
                if g["source_url"] not in seen:
                    seen.add(g["source_url"])
                    results.append(g)

        if results:
            logger.info(f"Xbox free games: {len(results)} total")
        else:
            logger.info("Xbox free games: none found")
        return results
