"""
RSSCollector: feedparserでRSSフィードを収集する
認証不要・完全無料
"""
import logging
from datetime import datetime
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from ..models.feed_item import FeedItem

logger = logging.getLogger(__name__)


class RSSCollector:
    """RSS/Atom フィードから記事を収集する"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; GadgetBlogBot/1.0)"
    }

    def collect(self, feeds_config: list[dict]) -> list[FeedItem]:
        """
        フィード設定リストを受け取り、FeedItemリストを返す

        Args:
            feeds_config: rss_feeds.yaml の feeds リスト

        Returns:
            収集したFeedItemのリスト
        """
        items: list[FeedItem] = []
        enabled_feeds = [f for f in feeds_config if f.get("enabled", True)]

        for feed_conf in enabled_feeds:
            try:
                feed_items = self._collect_feed(feed_conf)
                items.extend(feed_items)
                logger.info(
                    f"[RSS] {feed_conf['name']}: {len(feed_items)}件収集"
                )
            except Exception as e:
                logger.error(f"[RSS] {feed_conf['name']} 収集失敗: {e}")

        logger.info(f"[RSS] 合計 {len(items)}件収集")
        return items

    def _collect_feed(self, conf: dict) -> list[FeedItem]:
        """単一フィードを収集"""
        feed = feedparser.parse(
            conf["url"],
            request_headers=self.HEADERS
        )

        if feed.bozo and not feed.entries:
            logger.warning(f"[RSS] フィード取得エラー: {conf['url']}")
            return []

        items = []
        max_items = conf.get("max_items", 5)
        min_words = conf.get("min_body_words", 50)

        for entry in feed.entries[:max_items * 2]:  # 多めに取得してフィルタ
            item = self._parse_entry(entry, conf)
            if item is None:
                continue

            # 本文が短すぎるものを除外
            word_count = len(item.body.split())
            if word_count < min_words:
                continue

            items.append(item)
            if len(items) >= max_items:
                break

        return items

    def _parse_entry(self, entry, conf: dict) -> Optional[FeedItem]:
        """feedparserのentryをFeedItemに変換"""
        url = entry.get("link", "")
        title = entry.get("title", "")
        if not url or not title:
            return None

        # 本文取得(summary > content > description の優先度)
        raw_html = ""
        if hasattr(entry, "content") and entry.content:
            raw_html = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            raw_html = entry.summary
        elif hasattr(entry, "description"):
            raw_html = entry.description

        # HTML除去前に全画像URLを抽出
        image_urls = self._extract_all_images(raw_html)

        # HTML除去
        body = self._strip_html(raw_html)

        # 公開日時
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except Exception:
                pass

        # サムネイル (複数ソースから取得)
        thumbnail = ""
        # 1. media:thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            thumbnail = entry.media_thumbnail[0].get("url", "")
        # 2. media:content (画像タイプのみ)
        if not thumbnail and hasattr(entry, "media_content") and entry.media_content:
            for mc in entry.media_content:
                medium = mc.get("medium", "")
                mt = mc.get("type", "")
                if medium == "image" or mt.startswith("image/"):
                    thumbnail = mc.get("url", "")
                    break
        # 3. enclosure (podcast/image添付)
        if not thumbnail and hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("image/"):
                    thumbnail = enc.get("href", "")
                    break
        # 4. 抽出済み画像リストの先頭をサムネイルに使う
        if not thumbnail and image_urls:
            thumbnail = image_urls[0]

        return FeedItem(
            url=url,
            title=title,
            source=f"rss:{conf['name']}",
            category=conf.get("category", "テクノロジー"),
            body=body[:3000],  # 最大3000文字
            published_at=published_at,
            score=0,
            thumbnail_url=thumbnail,
            image_urls=image_urls,
            author=entry.get("author", ""),
        )

    @staticmethod
    def _extract_all_images(html: str) -> list:
        """HTMLから全img srcをhttps URLのみ抽出して返す"""
        if not html:
            return []
        try:
            soup = BeautifulSoup(html, "html.parser")
            urls = []
            seen = set()
            for img in soup.find_all("img"):
                src = img.get("src", "") or img.get("data-src", "")
                if src.startswith("https://") and src not in seen:
                    # トラッキングピクセル・アイコン系を除外 (1x1やsvgなど)
                    w = img.get("width", "100")
                    h = img.get("height", "100")
                    try:
                        if int(w) < 10 or int(h) < 10:
                            continue
                    except (ValueError, TypeError):
                        pass
                    seen.add(src)
                    urls.append(src)
            return urls
        except Exception:
            return []

    @staticmethod
    def _strip_html(html: str) -> str:
        """HTML タグを除去してプレーンテキストを返す"""
        if not html:
            return ""
        try:
            soup = BeautifulSoup(html, "lxml")
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            # lxmlが使えない場合のフォールバック
            try:
                soup = BeautifulSoup(html, "html.parser")
                return soup.get_text(separator=" ", strip=True)
            except Exception:
                return html
