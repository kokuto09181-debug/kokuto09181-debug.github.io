"""
Pipeline Orchestrator: 全ステージを繋ぐメインクラス

フロー:
  収集(Collect) → 重複除去(Dedup) → AI処理(Process) → 公開(Publish)
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..collectors.rss_collector import RSSCollector
from ..collectors.reddit_collector import RedditCollector
from ..collectors.dedup_store import DedupStore
from ..processors.claude_processor import ClaudeProcessor
from ..publishers.jekyll_publisher import JekyllPublisher
from ..publishers.git_publisher import GitPublisher
from ..publishers.social_publisher import SocialPublisher
from ..utils.config_loader import AppConfig

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"


@dataclass
class PipelineResult:
    """パイプライン実行結果のサマリー"""
    run_at: datetime = field(default_factory=datetime.utcnow)
    collected: int = 0
    after_dedup: int = 0
    processed: int = 0
    published: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = True


class Pipeline:
    """全パイプラインステージを統合するオーケストレーター"""

    def __init__(self, config: AppConfig):
        self.config = config

        # コレクター初期化
        self.rss_collector = RSSCollector()
        self.reddit_collector = RedditCollector()
        self.dedup = DedupStore(ttl_days=config.dedup_ttl_days)

        # プロセッサ初期化
        self.processor = ClaudeProcessor(
            api_key=config.api_key,
            default_model=config.default_model,
            featured_model=config.featured_model,
            max_tokens=config.max_tokens,
        )

        # パブリッシャー初期化
        self.jekyll_pub = JekyllPublisher(posts_dir=config.posts_dir)
        self.git_pub = GitPublisher(
            site_dir=config.site_dir,
            branch=config.git_branch,
            dry_run=config.git_dry_run,
        )
        self.social_pub = SocialPublisher()

        # データディレクトリ作成
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    def run(self) -> PipelineResult:
        """パイプラインをフル実行"""
        result = PipelineResult()
        logger.info("=" * 50)
        logger.info("パイプライン開始")

        # ステップ1: 収集
        raw_items = self._collect()
        result.collected = len(raw_items)
        if not raw_items:
            logger.warning("収集された記事が0件です")
            result.success = False
            return result

        # ステップ2: 重複除去
        new_items = self.dedup.filter_new(raw_items)
        result.after_dedup = len(new_items)
        if not new_items:
            logger.info("新規記事が0件 (全て処理済み)")
            return result

        # 上位N件に制限
        max_items = self.config.max_articles_per_run
        new_items = new_items[:max_items]

        # 最初の1件をfeatured (高品質モデル使用)
        for i, item in enumerate(new_items):
            item.is_featured = (i < self.config.featured_per_run)

        # デバッグ用にraw保存
        self._save_raw(new_items)

        # ステップ3: AI処理
        articles = self.processor.process_batch(new_items)
        result.processed = len(articles)
        if not articles:
            logger.error("AI処理結果が0件")
            result.success = False
            return result

        # デバッグ用にprocessed保存
        self._save_processed(articles)

        # ステップ4: 公開 (Jekyllファイル書き出し)
        published_count = self.jekyll_pub.publish_batch(articles)
        result.published = published_count

        # ステップ5: Git push (dry_run=Falseの場合のみ)
        if published_count > 0:
            self.git_pub.deploy(published_count)

        # ステップ6: SNS投稿 (認証情報が設定されている場合のみ)
        if articles:
            self.social_pub.publish_batch(articles)

        # ステップ7: 処理済みURLをdedupに登録
        for item in new_items:
            self.dedup.mark_seen(item.url)

        # 古いURL削除
        self.dedup.cleanup_old()

        logger.info(
            f"パイプライン完了: 収集={result.collected} "
            f"新規={result.after_dedup} "
            f"生成={result.processed} "
            f"公開={result.published}"
        )
        return result

    def _collect(self):
        """有効なコレクターから全記事を収集"""
        items = []
        collectors = self.config.enabled_collectors

        if "rss" in collectors:
            rss_items = self.rss_collector.collect(self.config.rss_feeds)
            items.extend(rss_items)

        if "reddit" in collectors:
            reddit_items = self.reddit_collector.collect(self.config.reddit_sources)
            items.extend(reddit_items)

        return items

    def _save_raw(self, items):
        """デバッグ用: rawデータをJSON保存"""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = RAW_DIR / f"raw_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in items], f, ensure_ascii=False, indent=2)

    def _save_processed(self, articles):
        """デバッグ用: processedデータをJSON保存"""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = PROCESSED_DIR / f"processed_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)
