"""
ClaudeProcessor: Anthropic APIで記事を日本語に変換・付加価値化する
"""
import json
import logging
import re
import time
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader

from ..models.feed_item import FeedItem
from ..models.article import ProcessedArticle
from .slug_generator import generate_slug

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


class ClaudeProcessor:
    """FeedItemをClaudeでProcessedArticleに変換する"""

    def __init__(self, api_key: str, default_model: str, featured_model: str, max_tokens: int = 4096):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = default_model
        self.featured_model = featured_model
        self.max_tokens = max_tokens
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR))
        )

    def process(self, item: FeedItem) -> ProcessedArticle | None:
        """
        FeedItemをClaudeで処理してProcessedArticleを返す
        失敗した場合はNoneを返す
        """
        model = self.featured_model if item.is_featured else self.default_model
        layout_type = self._detect_layout_type(item)
        prompt = self._build_prompt(item)

        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=self.max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                article_data = self._parse_response(content)
                if article_data is None:
                    logger.warning(f"[Processor] JSON解析失敗: {item.url}")
                    return None

                article = ProcessedArticle(
                    source_item=item,
                    ja_title=article_data.get("title", item.title),
                    ja_body=article_data.get("body", ""),
                    meta_description=article_data.get("meta_description", ""),
                    keywords=article_data.get("keywords", []),
                    category=article_data.get("category", item.category),
                    slug=generate_slug(article_data.get("title", item.title)),
                    layout_type=layout_type,
                    model_used=model,
                )
                logger.info(f"[Processor] 生成成功: {article.ja_title[:30]}...")
                return article

            except anthropic.RateLimitError:
                wait = 2 ** attempt * 10
                logger.warning(f"[Processor] レートリミット、{wait}秒待機...")
                time.sleep(wait)
            except anthropic.APIError as e:
                logger.error(f"[Processor] API Error: {e}")
                if attempt == 2:
                    return None
                time.sleep(5)

        return None

    def process_batch(self, items: list[FeedItem]) -> list[ProcessedArticle]:
        """複数FeedItemを順次処理する"""
        articles = []
        for i, item in enumerate(items):
            logger.info(f"[Processor] {i+1}/{len(items)}: {item.title[:50]}")
            article = self.process(item)
            if article:
                articles.append(article)
            # API連打防止
            if i < len(items) - 1:
                time.sleep(1.0)

        logger.info(f"[Processor] {len(articles)}/{len(items)}件 生成完了")
        return articles

    @staticmethod
    def _detect_layout_type(item: FeedItem) -> str:
        """カテゴリ・タイトルからレイアウト種別を判定"""
        text = (item.title + " " + item.category).lower()
        review_kw = ["review", "レビュー", "実機", "使ってみた", "開封", "hands-on"]
        comparison_kw = ["比較", "vs", " or ", "どっち", "comparison", "versus", "選び方"]
        if any(k in text for k in comparison_kw):
            return "comparison"
        if any(k in text for k in review_kw):
            return "review"
        return "general"

    def _build_prompt(self, item: FeedItem) -> str:
        """Jinja2テンプレートからプロンプトを生成"""
        template = self.jinja_env.get_template("article_generation.j2")
        body_excerpt = item.body[:1500] if item.body else "(本文なし)"
        layout_type = self._detect_layout_type(item)
        return template.render(
            title=item.title,
            url=item.url,
            category=item.category,
            body_excerpt=body_excerpt,
            layout_type=layout_type,
        )

    @staticmethod
    def _parse_response(content: str) -> dict | None:
        """Claude応答からJSONを抽出してパース"""
        # マークダウンのコードブロックを除去
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()

        # JSON部分を抽出(波括弧で囲まれた最初のブロック)
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}\nContent: {content[:200]}")
            return None
