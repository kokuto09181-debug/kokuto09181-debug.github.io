"""
SaleProcessor: セールイベント記事を自動生成する

セールカレンダーに基づき、イベント前に自動的にセール記事を生成。
通常価格 vs セール価格の比較とおすすめ度を含む。
"""
import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
import yaml
from jinja2 import Environment, FileSystemLoader

from ..models.feed_item import FeedItem
from ..models.article import ProcessedArticle

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"
EVENTS_DIR = Path(__file__).parent.parent.parent / "config" / "events"


class SaleProcessor:
    """セール記事を生成するプロセッサ"""

    def __init__(self, api_key: str, model: str, max_tokens: int = 8192):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.jinja_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))
        self.events = self._load_events()

    def _load_events(self) -> list[dict]:
        """セールカレンダーを読み込む"""
        calendar_path = EVENTS_DIR / "sale_calendar.yaml"
        if not calendar_path.exists():
            logger.warning("[Sale] セールカレンダーが見つかりません")
            return []
        with open(calendar_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("events", [])

    def get_upcoming_events(self) -> list[dict]:
        """記事を生成すべき直近のセールイベントを返す"""
        today = datetime.utcnow().date()
        upcoming = []
        for event in self.events:
            start = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
            pre_days = event.get("pre_article_days", 7)
            # セール開始のpre_days前〜セール終了日までが記事生成期間
            end = datetime.strptime(event["end_date"], "%Y-%m-%d").date()
            article_start = start - timedelta(days=pre_days)
            if article_start <= today <= end and event.get("products"):
                upcoming.append(event)
        return upcoming

    def generate(self, event: dict) -> ProcessedArticle | None:
        """セールイベントの記事を生成"""
        template = self.jinja_env.get_template("sale_article_generation.j2")
        prompt = template.render(
            event_name=event["name"],
            start_date=event["start_date"],
            end_date=event["end_date"],
            store=event.get("store", "amazon"),
            categories=event.get("categories", ["ガジェット"]),
            products=event.get("products", []),
        )

        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.content[0].text
                data = self._parse_response(content)
                if data is None:
                    logger.warning("[Sale] JSON解析失敗")
                    return None

                slug = event["slug"]
                now = datetime.utcnow()

                article = ProcessedArticle(
                    source_item=FeedItem(
                        url=f"sale://{slug}",
                        title=data.get("title", ""),
                        source="sale-event",
                        category=event.get("categories", ["ガジェット"])[0],
                    ),
                    ja_title=data.get("title", ""),
                    ja_body=data.get("body", ""),
                    meta_description=data.get("meta_description", ""),
                    keywords=data.get("keywords", []),
                    category=data.get("category", event.get("categories", ["ガジェット"])[0]),
                    slug=slug,
                    model_used=self.model,
                )
                logger.info(f"[Sale] 生成成功: {article.ja_title[:40]}...")
                return article

            except anthropic.RateLimitError:
                wait = 2 ** attempt * 10
                logger.warning(f"[Sale] レートリミット、{wait}秒待機...")
                time.sleep(wait)
            except anthropic.APIError as e:
                logger.error(f"[Sale] API Error: {e}")
                if attempt == 2:
                    return None
                time.sleep(5)

        return None

    @staticmethod
    def _parse_response(content: str) -> dict | None:
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.error(f"[Sale] JSON decode error: {e}")
            return None
