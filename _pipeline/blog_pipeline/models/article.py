"""
Article models: 収集→処理の変換後データ構造
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .feed_item import FeedItem


@dataclass
class ProcessedArticle:
    """Claudeが生成した日本語記事"""
    # 元情報
    source_item: FeedItem

    # Claude生成コンテンツ
    ja_title: str = ""
    ja_body: str = ""           # Markdown形式
    meta_description: str = ""
    keywords: list = field(default_factory=list)
    category: str = ""

    # 公開用メタ情報
    slug: str = ""              # URL用スラッグ
    layout_type: str = "general"  # "review" / "comparison" / "general"
    published_at: datetime = field(default_factory=datetime.utcnow)
    model_used: str = ""        # 使用したClaudeモデル

    # 状態
    is_published: bool = False
    processed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "source_item": self.source_item.to_dict(),
            "ja_title": self.ja_title,
            "ja_body": self.ja_body,
            "meta_description": self.meta_description,
            "keywords": self.keywords,
            "category": self.category,
            "slug": self.slug,
            "layout_type": self.layout_type,
            "published_at": self.published_at.isoformat(),
            "model_used": self.model_used,
            "is_published": self.is_published,
            "processed_at": self.processed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessedArticle":
        data = data.copy()
        data["source_item"] = FeedItem.from_dict(data["source_item"])
        data["published_at"] = datetime.fromisoformat(data["published_at"])
        data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        data.setdefault("layout_type", "general")
        return cls(**data)

    def to_jekyll_frontmatter(self) -> str:
        """Jekyll _posts用のYAML front matter文字列を生成"""
        kw_list = "\n".join(f'  - "{k}"' for k in self.keywords)
        thumbnail = self.source_item.thumbnail_url or ""
        thumbnail_line = f'\nthumbnail: "{thumbnail}"' if thumbnail else ""
        return f"""---
layout: post
title: "{self.ja_title.replace('"', "'")}"
date: {self.published_at.strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: [{self.category}]
tags:
{kw_list}
description: "{self.meta_description.replace('"', "'")}"
source_url: "{self.source_item.url}"
source_name: "{self.source_item.source}"
layout_type: "{self.layout_type}"{thumbnail_line}
---
"""
