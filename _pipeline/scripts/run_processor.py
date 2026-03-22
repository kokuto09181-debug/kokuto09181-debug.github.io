"""
run_processor.py: data/rawのJSONをAI処理してdata/processedに保存

使用方法:
  python scripts/run_processor.py                     # 最新のrawファイルを処理
  python scripts/run_processor.py --file data/raw/xxx.json
  python scripts/run_processor.py --model claude-sonnet-4-6  # モデル上書き
  python scripts/run_processor.py --limit 3           # 3件のみ処理
"""
import argparse
import json
import sys
from datetime import datetime
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
from blog_pipeline.models.feed_item import FeedItem
from blog_pipeline.processors.claude_processor import ClaudeProcessor


def main():
    parser = argparse.ArgumentParser(description="AI処理ステージのみ実行")
    parser.add_argument("--file", help="処理するrawJSONファイル(省略時は最新)")
    parser.add_argument("--model", help="使用するClaudeモデルの上書き")
    parser.add_argument("--limit", type=int, default=3, help="処理件数制限(デフォルト3)")
    args = parser.parse_args()

    config = load_config()
    setup_logger("DEBUG", config.log_file)

    # rawファイルを特定
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    if args.file:
        raw_file = Path(args.file)
    else:
        raw_files = sorted(raw_dir.glob("raw_*.json"))
        if not raw_files:
            print("rawファイルが見つかりません。先に run_collector.py を実行してください")
            sys.exit(1)
        raw_file = raw_files[-1]

    print(f"処理ファイル: {raw_file}")

    with open(raw_file, encoding="utf-8") as f:
        raw_data = json.load(f)

    items = [FeedItem.from_dict(d) for d in raw_data[:args.limit]]
    print(f"{len(items)}件を処理します\n")

    model = args.model or config.default_model
    processor = ClaudeProcessor(
        api_key=config.api_key,
        default_model=model,
        featured_model=model,
        max_tokens=config.max_tokens,
    )

    articles = processor.process_batch(items)

    # 結果表示
    print(f"\n生成完了: {len(articles)}件\n")
    for article in articles:
        print(f"  タイトル: {article.ja_title}")
        print(f"  カテゴリ: {article.category}")
        print(f"  キーワード: {', '.join(article.keywords)}")
        print(f"  スラッグ: {article.slug}")
        print()

    # processed保存
    processed_dir = Path(__file__).parent.parent / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output = processed_dir / f"processed_{ts}.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)
    print(f"保存: {output}")


if __name__ == "__main__":
    main()
