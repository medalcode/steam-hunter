import logging
import re
import requests
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

STEAM_URL_RE = re.compile(r"store\.steampowered\.com/app/(\d+)")

class GiveawayAPIScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
        })
        self._steam_url_cache: dict[str, str] = {}

    def _resolve_steam_url(self, page_url: str) -> str:
        if page_url in self._steam_url_cache:
            return self._steam_url_cache[page_url]
        try:
            resp = self.session.get(
                page_url, timeout=10,
                headers={"Accept": "text/html", "User-Agent": random.choice(USER_AGENTS)},
            )
            if resp.status_code == 200:
                m = STEAM_URL_RE.search(resp.text)
                if m:
                    url = f"https://store.steampowered.com/app/{m.group(1)}"
                    self._steam_url_cache[page_url] = url
                    return url
        except Exception:
            pass
        self._steam_url_cache[page_url] = ""
        return ""

    def search_all(self) -> list[dict]:
        results = []
        results.extend(self._freesteamkeys_giveaways())
        results.extend(self._gamerpower_giveaways())
        results.extend(self._givee_club())
        return results

    def _freesteamkeys_giveaways(self) -> list[dict]:
        try:
            resp = self.session.get(
                "https://www.freesteamkeys.com/api/giveaways?type=game",
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"freesteamkeys.com API -> {resp.status_code}")
                return []

            try:
                data = resp.json()
            except ValueError as e:
                logger.warning(f"freesteamkeys JSON decode error: {e}")
                return []

            now = datetime.now(timezone.utc).isoformat()
            results = []

            for item in data:
                title = item.get("title", "").strip()
                redemption = item.get("redemption", "")
                trust_score = item.get("trust_score", 0)
                source = item.get("source", "Unknown")

                steam_url = ""
                desc = item.get("description", "")
                m = STEAM_URL_RE.search(desc)
                if m:
                    steam_url = f"https://store.steampowered.com/app/{m.group(1)}"

                source_name = f"freesteamkeys/{trust_score}"
                if redemption == "Steam Activation":
                    source_name = "freesteamkeys/free"

                page_url = item.get("freesteamkeys_link") or item.get("giveaway_url", "")
                if not steam_url and page_url and redemption == "Steam Activation":
                    steam_url = self._resolve_steam_url(page_url)

                results.append({
                    "source": source_name,
                    "source_url": steam_url or page_url,
                    "title": f"FSK: {title[:200]}",
                    "description": desc[:500] if desc else "",
                    "found_at": now,
                })

            if results:
                logger.info(f"FreeSteamKeys API: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"FreeSteamKeys API error: {e}")
            return []

    def _givee_club(self) -> list[dict]:
        try:
            resp = self.session.get(
                "https://givee.club/es",
                timeout=15,
                headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            )
            if resp.status_code != 200:
                logger.warning(f"givee.club -> {resp.status_code}")
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            now = datetime.now(timezone.utc).isoformat()
            results = []

            for card in soup.select("a.event-card"):
                href = card.get("href", "")
                title_el = card.select_one("div.vertical-align-middle")
                if not title_el:
                    continue
                title = title_el.text.strip()
                if not title or len(title) < 3:
                    continue

                platform = "Steam"
                platform_el = card.select_one("i[class*='event-platform']")
                if platform_el:
                    cls = " ".join(platform_el.get("class", []))
                    if "epic" in cls.lower():
                        platform = "Epic Games"
                    elif "gog" in cls.lower():
                        platform = "GOG"

                event_url = f"https://givee.club{href}" if not href.startswith("http") else href

                steam_url = ""
                if platform == "Steam":
                    steam_url = self._resolve_steam_url(event_url)

                results.append({
                    "source": "giveeclub/free" if platform == "Steam" else "giveeclub/other",
                    "source_url": steam_url or event_url,
                    "title": f"Givee: {title[:200]}",
                    "description": f"Platform: {platform} | {event_url}",
                    "found_at": now,
                })

            if results:
                logger.info(f"Givee.Club: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Givee.Club error: {e}")
            return []

    def _gamerpower_giveaways(self) -> list[dict]:
        try:
            resp = self.session.get(
                "https://gamerpower.com/api/giveaways?platform=steam&type=game",
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"gamerpower.com API -> {resp.status_code}")
                return []

            try:
                data = resp.json()
            except ValueError as e:
                logger.warning(f"GamerPower JSON decode error: {e}")
                return []

            now = datetime.now(timezone.utc).isoformat()
            results = []

            for item in data:
                title = item.get("title", "").strip()
                status = item.get("status", "")
                if status != "Active":
                    continue
                steam_url = item.get("open_giveaway_url") or item.get("open_giveaway", "")

                results.append({
                    "source": "gamerpower/free",
                    "source_url": steam_url,
                    "title": f"GP: {title[:200]}",
                    "description": (item.get("description", "") or "")[:500],
                    "found_at": now,
                })

            if results:
                logger.info(f"GamerPower API: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"GamerPower API error: {e}")
            return []
