"""
SocialPublisher: 記事をThreadsに自動投稿する

必要な環境変数:
  THREADS_USER_ID      : 数値のユーザーID (me?fields=id で取得)
  THREADS_ACCESS_TOKEN : 長期アクセストークン (60日有効)
"""
import logging
import os
import random
import time
from datetime import datetime

import requests

from ..models.article import ProcessedArticle

logger = logging.getLogger(__name__)

SITE_URL = "https://gadgetpost.uk"

# セール期間中のThreads投稿テンプレート
SALE_TEMPLATES = [
    "🔥 {title}\n\n{highlight}\n\n{tags}\n{url}",
    "⚡ セール速報！\n{title}\n\n{highlight}\n\n{tags}\n{url}",
    "💰 今がお得！\n{title}\n\n{highlight}\n\n{tags}\n{url}",
    "🛒 見逃し注意！\n{title}\n\n{highlight}\n\n{tags}\n{url}",
    "📢 セール情報\n{title}\n\n{highlight}\n\n{tags}\n{url}",
]

SALE_HIGHLIGHTS = [
    "通常価格から最大63%OFF！Echo Dotが2,980円は底値級です。",
    "AirPods Pro 2が32,800円。Amazonの新生活セールが熱い🔥",
    "Sony WF-1000XM5が20%OFF。ノイキャン最強イヤホンがお買い得。",
    "新生活セールのおすすめをジャンル別にまとめました📱🎧🔋",
    "Fire TV Stick 4K Maxが40%OFF。テレビをスマートTVに。",
    "Anker充電器が27%OFF。コンパクトなのに67W出力。",
    "Kindle Paperwhiteが6,000円引き。読書好きは今がチャンス📚",
]


def _article_url(article: ProcessedArticle) -> str:
    d = article.published_at
    return f"{SITE_URL}/posts/{d.year}/{d.month:02d}/{article.slug}/"


def _build_post_text(article: ProcessedArticle) -> str:
    """投稿テキストを組み立てる (500字以内)"""
    url = _article_url(article)
    tags = " ".join(f"#{k.replace(' ', '')}" for k in article.keywords[:3])
    title = article.ja_title
    text = f"{title}\n\n{tags}\n{url}"
    if len(text) <= 500:
        return text
    max_title = 500 - len(f"\n\n{tags}\n{url}") - 3
    return f"{title[:max_title]}...\n\n{tags}\n{url}"


def _build_sale_post_text() -> str:
    """セール期間中の定期投稿テキストを生成"""
    template = random.choice(SALE_TEMPLATES)
    highlight = random.choice(SALE_HIGHLIGHTS)
    url = f"{SITE_URL}/sale/amazon-spring-2026/"
    tags = "#Amazonセール #新生活セール #ガジェット #お得情報"
    title = "Amazon新生活セール2026 おすすめ目玉商品まとめ"
    text = template.format(
        title=title,
        highlight=highlight,
        tags=tags,
        url=url,
    )
    return text[:500]


class SocialPublisher:
    """Threads への投稿を管理する"""

    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(self):
        self.user_id = os.environ.get("THREADS_USER_ID", "")
        self.access_token = os.environ.get("THREADS_ACCESS_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.user_id and self.access_token)

    def _post_to_threads(self, text: str) -> bool:
        """Threadsに1件投稿する共通メソッド"""
        if not self.is_configured:
            logger.info("[Threads] 認証情報未設定のためスキップ")
            return False

        try:
            # ステップ1: コンテナ作成
            container_resp = requests.post(
                f"{self.BASE_URL}/{self.user_id}/threads",
                params={
                    "media_type": "TEXT",
                    "text": text,
                    "access_token": self.access_token,
                },
                timeout=15
            )
            if container_resp.status_code != 200:
                logger.warning(f"[Threads] コンテナ作成失敗: {container_resp.status_code} {container_resp.text[:200]}")
                return False

            container_id = container_resp.json().get("id", "")
            if not container_id:
                logger.warning("[Threads] container_id が取得できません")
                return False

            time.sleep(3)

            # ステップ2: 公開
            publish_resp = requests.post(
                f"{self.BASE_URL}/{self.user_id}/threads_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                },
                timeout=15
            )
            if publish_resp.status_code == 200:
                post_id = publish_resp.json().get("id", "")
                logger.info(f"[Threads] 投稿成功: post_id={post_id}")
                return True
            else:
                logger.warning(f"[Threads] 公開失敗: {publish_resp.status_code} {publish_resp.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"[Threads] 投稿エラー: {e}")
            return False

    def publish_article(self, article: ProcessedArticle) -> bool:
        text = _build_post_text(article)
        return self._post_to_threads(text)

    def publish_sale_promo(self) -> bool:
        """セール期間中の定期プロモーション投稿"""
        text = _build_sale_post_text()
        logger.info(f"[Threads] セールプロモ投稿: {text[:60]}...")
        return self._post_to_threads(text)

    def publish_batch(self, articles: list[ProcessedArticle]) -> int:
        """複数記事を投稿。成功数を返す"""
        success = 0
        for i, article in enumerate(articles):
            if self.publish_article(article):
                success += 1
            if i < len(articles) - 1:
                time.sleep(2)
        logger.info(f"[Threads] {success}/{len(articles)}件 投稿完了")
        return success
