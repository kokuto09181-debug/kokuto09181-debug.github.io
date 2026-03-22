"""
SocialPublisher: 記事をThreadsに自動投稿する

必要な環境変数:
  THREADS_USER_ID      : 数値のユーザーID (me?fields=id で取得)
  THREADS_ACCESS_TOKEN : 長期アクセストークン (60日有効)
"""
import logging
import os
import time

import requests

from ..models.article import ProcessedArticle

logger = logging.getLogger(__name__)

SITE_URL = "https://gadgetpost.uk"


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


class SocialPublisher:
    """Threads への投稿を管理する"""

    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(self):
        self.user_id = os.environ.get("THREADS_USER_ID", "")
        self.access_token = os.environ.get("THREADS_ACCESS_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.user_id and self.access_token)

    def publish_article(self, article: ProcessedArticle) -> bool:
        if not self.is_configured:
            logger.info("[Threads] 認証情報未設定のためスキップ")
            return False

        try:
            text = _build_post_text(article)

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
