import re
import logging
import requests

logger = logging.getLogger(__name__)

STEAM_KEY_PATTERN = re.compile(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$')

def validate_key_format(key: str) -> dict:
    key = key.strip().upper()
    if not STEAM_KEY_PATTERN.match(key):
        return {"valid": False, "reason": "Invalid format (expected XXXXX-XXXXX-XXXXX)"}
    return {"valid": True, "reason": ""}

def validate_key_steam(key: str, session_cookies: dict | None = None) -> dict:
    result = validate_key_format(key)
    if not result["valid"]:
        return result

    if not session_cookies:
        return {"valid": True, "reason": "Format OK (no session to verify with Steam)"}

    session = requests.Session()
    for name, value in (session_cookies or {}).items():
        session.cookies.set(name, value)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://store.steampowered.com/",
    })

    try:
        resp = session.post(
            "https://store.steampowered.com/account/ajaxregisterkey",
            data={"product_key": key},
            timeout=10,
        )
        data = resp.json()
        success = data.get("success", -1)

        if success == 1:
            purchase = data.get("purchase_result", {})
            if purchase.get("purchase_result") == 0:
                return {"valid": True, "reason": "Valid and redeemable"}
            elif purchase.get("purchase_result") == 9:
                return {"valid": False, "reason": "Invalid key (Steam rejected)"}
            else:
                detail = purchase.get("purchase_result_details", "")
                return {"valid": True, "reason": f"Valid but may have issue: {detail}"}
        elif success == 24:
            return {"valid": False, "reason": "Duplicate key (already owned)"}
        elif success == 9:
            return {"valid": False, "reason": "Invalid key"}
        else:
            return {"valid": True, "reason": f"Unknown Steam response ({success})"}

    except requests.RequestException as e:
        logger.error(f"Validation HTTP error: {e}")
        return {"valid": True, "reason": f"Validation unavailable ({e})"}
    except ValueError:
        return {"valid": True, "reason": "Validation unavailable (parse error)"}

def validate_gift_link(url: str) -> dict:
    pattern = re.compile(
        r'^https?://store\.steampowered\.com/(?:friend|gift)/[a-zA-Z0-9]+'
    )
    if pattern.match(url):
        return {"valid": True, "reason": "Valid gift link format"}
    return {"valid": False, "reason": "Invalid gift link format"}

def validate_giveaway_url(url: str) -> dict:
    known_domains = [
        "gleam.io", "steamgifts.com", "giveaway.su",
        "steamtrades.com", "opium.pw",
    ]
    for domain in known_domains:
        if domain in url.lower():
            return {"valid": True, "reason": f"Known giveaway platform: {domain}"}

    try:
        resp = requests.head(url, timeout=5)
        if resp.status_code >= 400:
            return {"valid": False, "reason": f"URL is not reachable (HTTP {resp.status_code})"}
    except requests.RequestException:
        return {"valid": False, "reason": "URL is not reachable (connection failed)"}

    return {"valid": False, "reason": "Unknown giveaway platform (proceed with caution)"}
