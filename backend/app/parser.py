import re

STEAM_KEY_PATTERN = re.compile(
    r'\b[A-Z0-9\?]{5}(?:-[A-Z0-9\?]{5}){2}\b'
)

STEAM_GIFT_URL_PATTERN = re.compile(
    r'https?://store\.steampowered\.com/(?:friend|gift)/[a-zA-Z0-9]+'
)

GIVEAWAY_URL_PATTERNS = [
    re.compile(r'https?://www\.gleam\.io/contest/[a-zA-Z0-9_-]+'),
    re.compile(r'https?://giveaway\.su/[a-zA-Z0-9_-]+'),
    re.compile(r'https?://www\.steamgifts\.com/giveaway/[a-zA-Z0-9_-]+'),
    re.compile(r'https?://www\.steamtrades\.com/giveaway/[a-zA-Z0-9_-]+'),
    re.compile(r'https?://steam\.com/[a-zA-Z0-9/_-]*giveaway'),
]

def parse_steam_keys(text: str) -> list[str]:
    if not text:
        return []
    
    upper_text = text.upper()
    keys = STEAM_KEY_PATTERN.findall(upper_text)
    
    resolved_keys = []
    for k in keys:
        if '?' in k:
            # Try to find a hint like ? = X, ? is X, ?: X, ? -> X
            match = re.search(r'\?\s*(?:=|IS|:|->)\s*([A-Z0-9])', upper_text)
            if match:
                k = k.replace('?', match.group(1))
            else:
                # If we cannot resolve the mask, we discard it to avoid 10-fail ban from ASF
                continue
        resolved_keys.append(k)
        
    return list(set(resolved_keys))

def parse_gift_links(text: str) -> list[str]:
    if not text:
        return []
    return STEAM_GIFT_URL_PATTERN.findall(text)

def parse_giveaway_links(text: str) -> list[str]:
    if not text:
        return []
    links = []
    for pattern in GIVEAWAY_URL_PATTERNS:
        links.extend(pattern.findall(text))
    return list(set(links))

def parse_all(text: str) -> dict:
    return {
        "keys": parse_steam_keys(text),
        "gift_links": parse_gift_links(text),
        "giveaway_links": parse_giveaway_links(text),
    }
