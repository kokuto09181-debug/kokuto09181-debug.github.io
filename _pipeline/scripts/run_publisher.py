"""
run_publisher.py: data/processedのJSONをJekyllファイルとして書き出す

使用方法:
  python scripts/run_publisher.py            # 最新のprocessedファイルを公開
  python scripts/run_publisher.py --file data/processed/xxx.json
  python scripts/run_publisher.py --push     # git pushも実行 (dry_run上書き)
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
from blog_pipeline.models.article import ProcessedArticle
from blog_pipeline.publishers.jekyll_publisher import JekyllPublisher
from blog_pipeline.publishers.git_publisher import GitPublisher


def main():
    parser = argparse.ArgumentParser(description="公開ステージのみ実行")
    parser.add_argument("--file", help="処理するprocessed JSONファイル")
    parser.add_argument("--push", action="store_true", help="git pushも実行")
    args = parser.parse_args()

    config = load_config()
    setup_logger("DEBUG", config.log_file)

    # processedファイルを特定
    processed_dir = Path(__file__).parent.parent / "data" / "processed"
    if args.file:
        proc_file = Path(args.file)
    else:
        proc_files = sorted(processed_dir.glob("processed_*.json"))
        if not proc_files:
            print("processedファイルが見つかりません。先に run_processor.py を実行してください")
            sys.exit(1)
        proc_file = proc_files[-1]

    print(f"公開ファイル: {proc_file}")

    with open(proc_file, encoding="utf-8") as f:
        data = json.load(f)

    articles = [ProcessedArticle.from_dict(d) for d in data]
    print(f"{len(articles)}件を公開します\n")

    jekyll_pub = JekyllPublisher(posts_dir=config.posts_dir)
    count = jekyll_pub.publish_batch(articles)
    print(f"\n{count}件のMarkdownファイルを生成しました")
    print(f"場所: {config.posts_dir}")

    if args.push:
        git_pub = GitPublisher(
            site_dir=config.site_dir,
            branch=config.git_branch,
            dry_run=False,  # --pushが指定されたので強制push
        )
        git_pub.deploy(count)
        print("GitHub Pagesにpushしました")


if __name__ == "__main__":
    main()
