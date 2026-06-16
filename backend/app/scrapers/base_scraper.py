import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def make_result(source: str, title: str, source_url: str = "", description: str = "") -> dict[str, Any]:
    return {
        "source": source,
        "source_url": source_url,
        "title": title[:200],
        "description": description,
        "found_at": datetime.now(timezone.utc).isoformat(),
    }


class BaseScraper(ABC):
    def __init__(self, use_cloudscraper: bool = False):
        self.session = requests.Session()
        self.use_cloudscraper = use_cloudscraper
        if use_cloudscraper:
            import cloudscraper
            self.scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False, "desktop": True},
            )

    def _headers(self) -> dict[str, str]:
        return {
            **BASE_HEADERS,
            "User-Agent": random.choice(USER_AGENTS),
        }

    def _fetch(self, url: str, max_retries: int = 2, timeout: int = 20) -> requests.Response | None:
        for attempt in range(max_retries):
            try:
                if self.use_cloudscraper:
                    resp = self.scraper.get(url, timeout=timeout)
                else:
                    resp = self.session.get(url, headers=self._headers(), timeout=timeout)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"{self.__class__.__name__} {url} -> {resp.status_code}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)
            except requests.RequestException as e:
                logger.warning(f"{self.__class__.__name__} fetch error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        return None

    def _fetch_text(self, url: str, max_retries: int = 2, timeout: int = 20) -> str | None:
        resp = self._fetch(url, max_retries=max_retries, timeout=timeout)
        return resp.text if resp is not None else None

    def _fetch_json(self, url: str, max_retries: int = 2, timeout: int = 20) -> Any | None:
        resp = self._fetch(url, max_retries=max_retries, timeout=timeout)
        if resp is not None:
            try:
                return resp.json()
            except ValueError as e:
                logger.warning(f"{self.__class__.__name__} JSON decode error on {url}: {e}")
        return None

    @abstractmethod
    def search_freebies(self) -> list[dict[str, Any]]:
        ...
