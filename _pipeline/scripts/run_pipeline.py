"""
run_pipeline.py: パイプラインをフル実行するエントリーポイント

使用方法:
  # 通常実行 (config.yamlに従う)
  python scripts/run_pipeline.py

  # dry_run強制 (git pushしない)
  python scripts/run_pipeline.py --dry-run

  # 記事数を上書き
  python scripts/run_pipeline.py --max-articles 5
"""
import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# .envファイルを読み込む
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass  # python-dotenvが入っていなければ環境変数から直接読む

from blog_pipeline.utils.config_loader import load_config
from blog_pipeline.utils.logger import setup_logger
from blog_pipeline.pipeline.orchestrator import Pipeline


def main():
    parser = argparse.ArgumentParser(description="ガジェットブログ自動生成パイプライン")
    parser.add_argument("--dry-run", action="store_true",
                        help="git pushをスキップ (ファイルは生成される)")
    parser.add_argument("--max-articles", type=int,
                        help="最大記事数の上書き")
    parser.add_argument("--no-reddit", action="store_true",
                        help="Reddit収集を無効化")
    parser.add_argument("--no-rss", action="store_true",
                        help="RSS収集を無効化")
    args = parser.parse_args()

    # 設定読み込み
    try:
        config = load_config()
    except ValueError as e:
        print(f"設定エラー: {e}", file=sys.stderr)
        sys.exit(1)

    # コマンドライン引数で上書き
    if args.dry_run:
        config.git_dry_run = True
    if args.max_articles:
        config.max_articles_per_run = args.max_articles
    if args.no_reddit:
        config.enabled_collectors = [c for c in config.enabled_collectors if c != "reddit"]
    if args.no_rss:
        config.enabled_collectors = [c for c in config.enabled_collectors if c != "rss"]

    # ロガー設定
    setup_logger(config.log_level, config.log_file)

    # パイプライン実行
    pipeline = Pipeline(config)
    result = pipeline.run()

    if result.success:
        print(f"\n✓ 完了: {result.published}件の記事を生成・公開しました")
        sys.exit(0)
    else:
        print(f"\n✗ エラーが発生しました: {result.errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
