import logging
import re
import time

logger = logging.getLogger(__name__)

GLEAM_DOMAINS = ["gleam.io", "gleam.io/competitions"]

class GleamAutoEnter:
    def __init__(self):
        self._playwright_available = False
        try:
            import playwright
            self._playwright_available = True
        except ImportError:
            pass

    def can_auto_enter(self, url: str) -> bool:
        return any(domain in url.lower() for domain in GLEAM_DOMAINS)

    def auto_enter(self, url: str, giveaway_title: str = "") -> dict:
        if not self._playwright_available:
            return {
                "success": False,
                "message": "Playwright not installed. Run: pip install playwright && playwright install chromium",
            }

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "success": False,
                "message": "Failed to import Playwright",
            }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

                entries = page.query_selector_all(
                    "a[href*='gleam.io'], .enter-button, .btn-enter, "
                    "button:has-text('Enter'), a:has-text('Enter')"
                )

                entered = False
                for entry in entries:
                    if entry.is_visible():
                        entry.click()
                        time.sleep(1)
                        entered = True
                        break

                browser.close()
                if entered:
                    return {"success": True, "message": "Auto-entered giveaway"}
                else:
                    return {"success": False, "message": "No enter button found (may need manual login)"}

            except Exception as e:
                browser.close()
                logger.error(f"Playwright error on {url}: {e}")
                return {"success": False, "message": f"Browser error: {e}"}

def auto_enter_giveaway(url: str, title: str = "") -> dict:
    engine = GleamAutoEnter()
    if engine.can_auto_enter(url):
        return engine.auto_enter(url, title)
    return {"success": False, "message": "Unsupported giveaway platform"}
