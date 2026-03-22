"""
run_collector.py: 収集ステージのみを実行してデバッグ

使用方法:
  python scripts/run_collector.py           # 全コレクター
  python scripts/run_collector.py --rss     # RSSのみ
  python scripts/run_collector.py --reddit  # Redditのみ
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

from blog_pipeline.utils.config_loader import load_config
from blog_pipeline.utils.logger import setup_logger
from blog_pipeline.collectors.rss_collector import RSSCollector
from blog_pipeline.collectors.reddit_collector import RedditCollector


def main():
    parser = argparse.ArgumentParser(description="収集ステージのみ実行")
    parser.add_argument("--rss", action="store_true", help="RSSのみ")
    parser.add_argument("--reddit", action="store_true", help="Redditのみ")
    args = parser.parse_args()

    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "dummy_for_collector")
    config = load_config()

    setup_logger("DEBUG", config.log_file)

    items = []
    use_all = not args.rss and not args.reddit

    if args.rss or use_all:
        collector = RSSCollector()
        rss_items = collector.collect(config.rss_feeds)
        items.extend(rss_items)
        print(f"\nRSS: {len(rss_items)}件")

    if args.reddit or use_all:
        collector = RedditCollector()
        reddit_items = collector.collect(config.reddit_sources)
        items.extend(reddit_items)
        print(f"Reddit: {len(reddit_items)}件")

    print(f"\n合計: {len(items)}件\n")
    for item in items[:5]:
        print(f"  [{item.source}] {item.title[:60]}")
        print(f"    URL: {item.url}")
        print(f"    カテゴリ: {item.category}, スコア: {item.score}")
        print()

    # data/rawに保存
    from datetime import datetime
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output = raw_dir / f"raw_{ts}.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in items], f, ensure_ascii=False, indent=2)
    print(f"保存: {output}")


if __name__ == "__main__":
    main()
