#!/usr/bin/env python3
"""Save Xbox cookies from browser Selenium session to the cookies file."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.scrapers.xbox_catalog import XBOX_COOKIES_FILE

TARGET = os.environ.get("XBOX_COOKIES_FILE", 
    os.path.join(os.path.dirname(__file__), "xbox_cookies.json"))


def save_cookies(cookie_dict: dict):
    with open(TARGET, "w") as f:
        json.dump(cookie_dict, f)
    print(f"Saved {len(cookie_dict)} cookies to {TARGET}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--from-stdin":
        raw = sys.stdin.read()
        cookies = {}
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                name, val = part.split("=", 1)
                cookies[name] = val
        save_cookies(cookies)
    else:
        print("Usage: echo '<cookie_string>' | python refresh_xbox_cookies.py --from-stdin")
