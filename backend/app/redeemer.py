import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

STEAM_REGISTER_KEY_URL = "https://store.steampowered.com/account/ajaxregisterkey"
STEAM_GIFT_ACCEPT_URL = "https://store.steampowered.com/friend/acceptgift/"

def redeem_key(session_cookies: dict, key: str) -> dict:
    session = requests.Session()
    for name, value in (session_cookies or {}).items():
        session.cookies.set(name, value)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://store.steampowered.com/",
    })

    try:
        resp = session.post(STEAM_REGISTER_KEY_URL, data={"product_key": key}, timeout=15)
        data = resp.json()

        if data.get("success") == 1:
            purchase_result = data.get("purchase_result", {})
            if purchase_result.get("purchase_result") == 0:
                return {"success": True, "message": "Key redeemed successfully"}
            else:
                error_msg = purchase_result.get("purchase_result_details", "Unknown error")
                return {"success": False, "message": f"Redeem error: {error_msg}"}
        elif data.get("success") == 24:
            return {"success": False, "message": "Duplicate key (already owned)"}
        elif data.get("success") == 9:
            return {"success": False, "message": "Invalid key"}
        else:
            return {"success": False, "message": f"Steam error {data.get('success')}: {data}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error redeeming key {key}: {e}")
        return {"success": False, "message": f"HTTP error: {e}"}
    except ValueError as e:
        logger.error(f"JSON parse error redeeming key {key}: {e}")
        return {"success": False, "message": f"Parse error: {e}"}

def accept_gift(session_cookies: dict, gift_link: str) -> dict:
    session = requests.Session()
    for name, value in (session_cookies or {}).items():
        session.cookies.set(name, value)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })

    try:
        resp = session.post(gift_link, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Gift accepted"}
        else:
            return {"success": False, "message": f"HTTP {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error accepting gift {gift_link}: {e}")
        return {"success": False, "message": f"HTTP error: {e}"}
