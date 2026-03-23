"""
ブログ新着記事 → Threads通知スクリプト
- _posts/ の新規ファイルを検出してThreadsに投稿
- GitHub Actions: push時に実行
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT      = Path(__file__).parent.parent.parent   # site/
POSTS_DIR = ROOT / "_posts"

BLOG_BASE = "https://gadgetpost.uk"
HASHTAGS  = "#ガジェット #テック #新着記事"


def get_new_post_files() -> list[Path]:
    """直前のコミットと比較して新しく追加された_posts/*.mdを返す"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=ROOT,
        )
        lines = result.stdout.strip().splitlines()
        new_files = []
        for line in lines:
            p = ROOT / line
            if p.suffix == ".md" and "_posts" in line:
                new_files.append(p)
        return new_files
    except Exception as e:
        print(f"[ERROR] git diff failed: {e}")
        return []


def parse_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except Exception:
        return {}


def build_post_url(path: Path, fm: dict) -> str:
    # Jekyll URLパターン: /YYYY/MM/DD/slug/
    stem = path.stem  # 例: 2026-03-22-my-article-20260322083036
    parts = stem.split("-")
    if len(parts) >= 3:
        year, month, day = parts[0], parts[1], parts[2]
        slug = "-".join(parts[3:])
        # タイムスタンプ末尾(14桁)を除去
        if len(parts[-1]) == 14 and parts[-1].isdigit():
            slug = "-".join(parts[3:-1])
        return f"{BLOG_BASE}/{year}/{month}/{day}/{slug}/"
    return BLOG_BASE


def build_text(fm: dict, url: str) -> str:
    title = fm.get("title", "新着記事")
    desc  = fm.get("description", "")

    text = f"📝 新着記事\n\n{title}"
    if desc:
        # 80文字以内に収める
        short = desc[:80] + ("…" if len(desc) > 80 else "")
        text += f"\n\n{short}"
    text += f"\n\n{url}\n\n{HASHTAGS}"
    return text[:500]


def post_to_threads(text: str) -> bool:
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not user_id or not token:
        print("[ERROR] THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定")
        return False

    base = "https://graph.threads.net/v1.0"
    r1 = requests.post(
        f"{base}/{user_id}/threads",
        params={"media_type": "TEXT", "text": text, "access_token": token},
        timeout=15,
    )
    if r1.status_code != 200:
        print(f"[ERROR] コンテナ作成失敗: {r1.status_code} {r1.text[:200]}")
        return False

    container_id = r1.json().get("id", "")
    time.sleep(3)

    r2 = requests.post(
        f"{base}/{user_id}/threads_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=15,
    )
    if r2.status_code == 200:
        print(f"[OK] 投稿成功: {r2.json().get('id','')}")
        return True
    print(f"[ERROR] 公開失敗: {r2.status_code} {r2.text[:200]}")
    return False


def main():
    dry_run = "--dry-run" in sys.argv
    new_files = get_new_post_files()

    if not new_files:
        print("[SKIP] 新着記事なし")
        return

    for path in new_files:
        fm  = parse_front_matter(path)
        url = build_post_url(path, fm)
        text = build_text(fm, url)

        print("=" * 50)
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        print("=" * 50)

        if dry_run:
            print("[DRY-RUN] 投稿スキップ")
            continue

        post_to_threads(text)


if __name__ == "__main__":
    main()
