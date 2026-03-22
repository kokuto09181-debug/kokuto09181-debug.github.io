"""
RedditCollector: Reddit公開JSONエンドポイントから記事を収集する
OAuth不要・完全無料 (User-Agent必須)
"""
import logging
import time
from datetime import datetime
from typing import Optional

import requests

from ..models.feed_item import FeedItem

logger = logging.getLogger(__name__)


class RedditCollector:
    """Reddit公開APIから人気投稿を収集する"""

    BASE_URL = "https://www.reddit.com"
    HEADERS = {
        # Redditはちゃんとしたユーザーエージェントを要求する
        "User-Agent": "GadgetBlogBot/1.0 (by /u/gadgetblogbot)"
    }
    REQUEST_DELAY = 1.0  # API連打防止

    def collect(self, subreddits_config: list[dict]) -> list[FeedItem]:
        """
        サブレディット設定リストから投稿を収集する

        Args:
            subreddits_config: reddit_sources.yaml の subreddits リスト

        Returns:
            収集したFeedItemのリスト
        """
        items: list[FeedItem] = []
        enabled = [s for s in subreddits_config if s.get("enabled", True)]

        for sub_conf in enabled:
            try:
                sub_items = self._collect_subreddit(sub_conf)
                items.extend(sub_items)
                logger.info(
                    f"[Reddit] r/{sub_conf['name']}: {len(sub_items)}件収集"
                )
                time.sleep(self.REQUEST_DELAY)
            except Exception as e:
                logger.error(f"[Reddit] r/{sub_conf['name']} 収集失敗: {e}")

        logger.info(f"[Reddit] 合計 {len(items)}件収集")
        return items

    def _collect_subreddit(self, conf: dict) -> list[FeedItem]:
        """単一サブレディットを収集"""
        subreddit = conf["name"]
        sort = conf.get("sort", "hot")
        limit = conf.get("limit", 10)
        min_score = conf.get("min_score", 50)
        time_filter = conf.get("time_filter", "day")

        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = {"limit": min(limit * 2, 25), "t": time_filter}

        resp = requests.get(url, headers=self.HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        posts = data.get("data", {}).get("children", [])
        items = []

        for post_data in posts:
            post = post_data.get("data", {})
            item = self._parse_post(post, conf)
            if item is None:
                continue

            # スコアフィルタ
            if item.score < min_score:
                continue

            # テキスト投稿のみ(リンク投稿は本文なし)
            if not item.body and post.get("is_self") is False:
                # リンク投稿でも外部URLがあればOK(urlとして記録済み)
                # ただし本文なしはAI処理に向かないのでタイトルのみ記事として扱う
                if len(item.title) < 20:
                    continue

            items.append(item)
            if len(items) >= limit:
                break

        return items

    def _parse_post(self, post: dict, conf: dict) -> Optional[FeedItem]:
        """Reddit投稿のdictをFeedItemに変換"""
        url = post.get("url", "")
        title = post.get("title", "")
        if not url or not title:
            return None

        # セルフポスト(テキスト投稿)の本文
        body = post.get("selftext", "") or ""
        if body == "[deleted]" or body == "[removed]":
            body = ""

        # 外部リンク投稿の場合はURLがそのまま記事URL
        # permalinkはRedditのスレッドURL
        reddit_url = f"{self.BASE_URL}{post.get('permalink', '')}"

        # 投稿日時
        created_utc = post.get("created_utc")
        published_at = None
        if created_utc:
            published_at = datetime.utcfromtimestamp(created_utc)

        # サムネイル
        thumbnail = post.get("thumbnail", "")
        if thumbnail in ("self", "default", "nsfw", "spoiler", ""):
            thumbnail = ""
        # preview画像があれば優先
        if post.get("preview", {}).get("images"):
            try:
                thumbnail = post["preview"]["images"][0]["source"]["url"]
                thumbnail = thumbnail.replace("&amp;", "&")
            except (KeyError, IndexError):
                pass

        return FeedItem(
            url=url if not post.get("is_self") else reddit_url,
            title=title,
            source=f"reddit:r/{conf['name']}",
            category=conf.get("category", "テクノロジー"),
            body=body[:3000],
            published_at=published_at,
            score=post.get("score", 0),
            thumbnail_url=thumbnail,
            author=post.get("author", ""),
        )
