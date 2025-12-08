import logging
import praw
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = [
    "FreeGameFindings",
    "GameDeals",
    "steam_giveaway",
    "steamdeals",
    "freebies",
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
                subreddit = self.reddit.get_subreddit(sub_name)
                for post in subreddit.new(limit=limit):
                    now = datetime.now(timezone.utc)
                    post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                    hours_ago = (now - post_time).total_seconds() / 3600

                    if hours_ago > 48:
                        continue

                    results.append({
                        "source": f"reddit/{sub_name}",
                        "source_url": f"https://reddit.com{post.permalink}",
                        "title": post.title,
                        "description": (post.selftext or "")[:2000],
                        "found_at": post_time.isoformat(),
                    })
            except Exception as e:
                logger.error(f"Error scraping r/{sub_name}: {e}")

        return results
