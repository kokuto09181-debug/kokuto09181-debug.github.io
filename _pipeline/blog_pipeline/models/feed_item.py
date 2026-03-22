"""
FeedItem: コレクターが返す正規化されたデータ構造
全コレクター(RSS/Reddit)はこの型で出力する
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FeedItem:
    """コレクターからプロセッサへ渡すデータ"""
    # 必須フィールド
    url: str
    title: str
    source: str          # "rss:The Verge" / "reddit:r/gadgets"
    category: str        # "ガジェット" など

    # 任意フィールド
    body: str = ""       # 本文抜粋(HTML除去済み)
    published_at: Optional[datetime] = None
    score: int = 0       # Redditのスコア(RSS=0)
    thumbnail_url: str = ""
    image_urls: list = field(default_factory=list)  # 元記事内の全画像URL
    author: str = ""

    # 内部管理
    collected_at: datetime = field(default_factory=datetime.utcnow)
    is_featured: bool = False  # Trueならhigh-qualityモデルで処理

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "body": self.body,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "score": self.score,
            "thumbnail_url": self.thumbnail_url,
            "image_urls": self.image_urls,
            "author": self.author,
            "collected_at": self.collected_at.isoformat(),
            "is_featured": self.is_featured,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedItem":
        data = data.copy()
        if data.get("published_at"):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        if data.get("collected_at"):
            data["collected_at"] = datetime.fromisoformat(data["collected_at"])
        return cls(**data)
