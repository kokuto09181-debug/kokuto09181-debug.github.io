"""
RoundupProcessor: 週次の「おすすめまとめ記事」を自動生成する

カテゴリ別にSEOに強い比較・おすすめ記事を生成。
アフィリエイトリンク付きで収益化に直結する。
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader

from ..models.feed_item import FeedItem
from ..models.article import ProcessedArticle
from .slug_generator import generate_slug

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"

# 週替わりで回すまとめ記事テーマ
ROUNDUP_TOPICS = [
    {
        "topic": "ワイヤレスイヤホンのおすすめ製品を比較紹介してください。AirPods Pro、Sony WF-1000XM6、Samsung Galaxy Buds 3 Pro、Google Pixel Buds Pro 2、Jabra Elite 10 Gen 2 などの最新モデルを含めてください。",
        "category": "ガジェット",
        "slug_hint": "wireless-earbuds-best",
    },
    {
        "topic": "2026年に買うべきおすすめスマートフォンを紹介してください。iPhone 17シリーズ、Galaxy S26シリーズ、Pixel 10シリーズ、Xiaomi 16シリーズ、Nothing Phone 4 などを含めてください。",
        "category": "スマートフォン",
        "slug_hint": "best-smartphones",
    },
    {
        "topic": "おすすめのノートPC・ノートパソコンを比較紹介してください。MacBook Air M4、Dell XPS、ThinkPad X1 Carbon、Surface Laptop、ASUS Zenbook などを含めてください。",
        "category": "PC・パーツ",
        "slug_hint": "best-laptops",
    },
    {
        "topic": "おすすめのスマートウォッチを比較紹介してください。Apple Watch Ultra 3、Apple Watch Series 11、Samsung Galaxy Watch 7、Google Pixel Watch 3、Garmin Venu 4 などを含めてください。",
        "category": "ガジェット",
        "slug_hint": "best-smartwatches",
    },
    {
        "topic": "おすすめのタブレットを比較紹介してください。iPad Pro M4、iPad Air M3、Samsung Galaxy Tab S10、Google Pixel Tablet 2、Xiaomi Pad 7 Pro などを含めてください。",
        "category": "ガジェット",
        "slug_hint": "best-tablets",
    },
    {
        "topic": "おすすめのモバイルバッテリー・充電器を比較紹介してください。Anker製品を中心に、CIO、Baseus、Belkin、UGREEN などのブランドも含めてください。",
        "category": "ガジェット",
        "slug_hint": "best-chargers-powerbanks",
    },
    {
        "topic": "おすすめのワイヤレスヘッドホンを比較紹介してください。Sony WH-1000XM6、Apple AirPods Max 2、Bose QuietComfort Ultra、Sennheiser Momentum 5、Audio-Technica ATH-M50xBT2 などを含めてください。",
        "category": "ガジェット",
        "slug_hint": "best-headphones",
    },
]


class RoundupProcessor:
    """まとめ記事を生成するプロセッサ"""

    def __init__(self, api_key: str, model: str, max_tokens: int = 8192):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.jinja_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))

    def generate(self, topic_index: int, recent_items: list[FeedItem] = None) -> ProcessedArticle | None:
        """指定インデックスのまとめ記事を生成"""
        topic_conf = ROUNDUP_TOPICS[topic_index % len(ROUNDUP_TOPICS)]
        recent_items = recent_items or []

        template = self.jinja_env.get_template("roundup_generation.j2")
        prompt = template.render(
            topic=topic_conf["topic"],
            category=topic_conf["category"],
            recent_items=[{"title": i.title, "source": i.source} for i in recent_items[:5]],
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
                    logger.warning("[Roundup] JSON解析失敗")
                    return None

                slug_base = topic_conf["slug_hint"]
                now = datetime.utcnow()
                slug = f"{slug_base}-{now.strftime('%Y%m')}"

                article = ProcessedArticle(
                    source_item=FeedItem(
                        url=f"roundup://{slug}",
                        title=data.get("title", ""),
                        source="roundup",
                        category=topic_conf["category"],
                    ),
                    ja_title=data.get("title", ""),
                    ja_body=data.get("body", ""),
                    meta_description=data.get("meta_description", ""),
                    keywords=data.get("keywords", []),
                    category=data.get("category", topic_conf["category"]),
                    slug=slug,
                    model_used=self.model,
                )
                logger.info(f"[Roundup] 生成成功: {article.ja_title[:40]}...")
                return article

            except anthropic.RateLimitError:
                wait = 2 ** attempt * 10
                logger.warning(f"[Roundup] レートリミット、{wait}秒待機...")
                time.sleep(wait)
            except anthropic.APIError as e:
                logger.error(f"[Roundup] API Error: {e}")
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
            logger.error(f"[Roundup] JSON decode error: {e}")
            return None

    @staticmethod
    def get_topic_for_today() -> int:
        """今日の日付に基づいてトピックインデックスを返す（週替わり）"""
        day_of_year = datetime.utcnow().timetuple().tm_yday
        week = day_of_year // 7
        return week % len(ROUNDUP_TOPICS)
