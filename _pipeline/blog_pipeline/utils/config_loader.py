"""
ConfigLoader: config.yamlと環境変数を統合してAppConfigを返す
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.yaml"
RSS_FEEDS_PATH = Path(__file__).parent.parent.parent / "config" / "sources" / "rss_feeds.yaml"
REDDIT_PATH = Path(__file__).parent.parent.parent / "config" / "sources" / "reddit_sources.yaml"


@dataclass
class AppConfig:
    """アプリケーション設定の型付きコンテナ"""
    # Anthropic
    api_key: str
    default_model: str
    featured_model: str
    max_tokens: int
    featured_per_run: int

    # Pipeline
    max_articles_per_run: int
    dedup_ttl_days: int
    enabled_collectors: list[str]

    # Publishers
    posts_dir: str
    site_dir: str
    git_branch: str
    git_dry_run: bool

    # Sources
    rss_feeds: list[dict]
    reddit_sources: list[dict]

    # Logging
    log_level: str
    log_file: str


def load_config(config_path: Path = CONFIG_PATH) -> AppConfig:
    """
    config.yamlを読み込み、${ENV_VAR}形式の環境変数を展開してAppConfigを返す
    """
    with open(config_path, encoding="utf-8") as f:
        raw = f.read()

    # ${VAR_NAME} 形式の環境変数を展開
    def replace_env(match):
        var_name = match.group(1)
        value = os.environ.get(var_name, "")
        if not value:
            raise ValueError(
                f"必須環境変数 {var_name} が設定されていません。"
                f"\n.env.example を参考に .env ファイルを作成するか、環境変数を設定してください。"
            )
        return value

    expanded = re.sub(r"\$\{([A-Z_][A-Z0-9_]*)\}", replace_env, raw)
    cfg = yaml.safe_load(expanded)

    # ソース設定を読み込む
    with open(RSS_FEEDS_PATH, encoding="utf-8") as f:
        rss_feeds = yaml.safe_load(f).get("feeds", [])

    with open(REDDIT_PATH, encoding="utf-8") as f:
        reddit_sources = yaml.safe_load(f).get("subreddits", [])

    return AppConfig(
        # Anthropic
        api_key=cfg["anthropic"]["api_key"],
        default_model=cfg["anthropic"]["default_model"],
        featured_model=cfg["anthropic"]["featured_model"],
        max_tokens=cfg["anthropic"]["max_tokens"],
        featured_per_run=cfg["anthropic"].get("featured_per_run", 1),

        # Pipeline
        max_articles_per_run=cfg["pipeline"]["max_articles_per_run"],
        dedup_ttl_days=cfg["pipeline"]["dedup_ttl_days"],
        enabled_collectors=cfg["pipeline"]["collectors"],

        # Publishers (POSTS_DIR/SITE_DIR環境変数でCI時に上書き可能)
        posts_dir=os.environ.get("POSTS_DIR") or cfg["publishers"]["github_pages"]["posts_dir"],
        site_dir=os.environ.get("SITE_DIR") or cfg["publishers"]["github_pages"]["site_dir"],
        git_branch=cfg["publishers"]["github_pages"]["branch"],
        git_dry_run=cfg["publishers"]["github_pages"].get("dry_run", True),

        # Sources
        rss_feeds=rss_feeds,
        reddit_sources=reddit_sources,

        # Logging
        log_level=cfg["logging"]["level"],
        log_file=cfg["logging"]["file"],
    )
