import logging
import praw
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = [
    "FreeGameFindings",
    "FreeGamesOnSteam",
    "GameDeals",
    "steam_giveaway",
    "steamdeals",
    "freebies",
    "RandomActsOfGaming",
    "GiftofGames",
    "pcmasterrace",
    "gaming",
    "FREE",
    "Freegamestuff",
]

class RedditScraper:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    def search_recent(self, subreddits: list[str] | None = None, limit: int = 25) -> list[dict]:
        targets = subreddits or DEFAULT_SUBREDDITS
        results = []

        for sub_name in targets:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                # 1. Scrape new posts
                for post in subreddit.new(limit=limit):
                    now = datetime.now(timezone.utc)
                    post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                    hours_ago = (now - post_time).total_seconds() / 3600

                    if hours_ago > 48:
                        continue

                    results.append({
                        "source": f"reddit/{sub_name}/post",
                        "source_url": f"https://reddit.com{post.permalink}",
                        "title": post.title,
                        "description": (post.selftext or "")[:2000],
                        "found_at": post_time.isoformat(),
                    })
                    
                # 2. Scrape new comments (highly effective for ninja keys)
                for comment in subreddit.comments(limit=limit):
                    now = datetime.now(timezone.utc)
                    comment_time = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
                    hours_ago = (now - comment_time).total_seconds() / 3600

                    if hours_ago > 48:
                        continue

                    # Only keep comments that likely contain a key or giveaway link
                    text = comment.body or ""
                    if "-" in text or "key" in text.lower() or "giveaway" in text.lower() or "http" in text:
                        results.append({
                            "source": f"reddit/{sub_name}/comment",
                            "source_url": f"https://reddit.com{comment.permalink}",
                            "title": f"Comment in r/{sub_name}",
                            "description": text[:2000],
                            "found_at": comment_time.isoformat(),
                        })

            except Exception as e:
                logger.error(f"Error scraping r/{sub_name}: {e}")

        return results
