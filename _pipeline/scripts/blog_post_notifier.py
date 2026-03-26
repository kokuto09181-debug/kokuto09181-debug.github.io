"""
ブログ新着記事 → Threads通知スクリプト
- _posts/ の新規ファイルを検出してThreadsに投稿
- 複数記事が同時追加された場合は最も注目度の高い1件のみ投稿（連投防止）
- GitHub Actions: push時に実行
"""

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
HASHTAG   = "#ガジェット"   # Threads仕様: 1投稿1タグのみ有効


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


def pick_best(files: list[Path]) -> Path:
    """複数ある場合は最も注目度の高い1件を選ぶ（セール記事 > レビュー > 一般）"""
    sale_kw = ["sale", "セール", "割引", "off", "お得"]
    review_kw = ["review", "レビュー", "比較", "おすすめ"]

    def score(p: Path) -> int:
        name = p.stem.lower()
        fm = parse_front_matter(p)
        title = (fm.get("title", "") + " " + name).lower()
        if any(k in title for k in sale_kw):
            return 2
        if any(k in title for k in review_kw):
            return 1
        return 0

    return max(files, key=score)


def build_post_url(path: Path) -> str:
    # Jekyll URLパターン: /posts/YYYY/MM/title/
    # :title = ファイル名からYYYY-MM-DD-を除いた部分（タイムスタンプ含む）
    stem = path.stem
    parts = stem.split("-")
    if len(parts) >= 4:
        year, month = parts[0], parts[1]
        slug = "-".join(parts[3:])
        return f"{BLOG_BASE}/posts/{year}/{month}/{slug}/"
    return BLOG_BASE


def build_text(fm: dict, url: str) -> str:
    title = fm.get("title", "新着記事")
    desc  = fm.get("description", "")
    tags  = fm.get("tags", []) or []
    category = fm.get("categories", ["ガジェット"])
    if isinstance(category, list):
        category = category[0] if category else "ガジェット"

    # 冒頭：カテゴリラベル
    lines = [f"📝 {category}の新着記事", "", title]

    # 説明文（あれば）
    if desc:
        short = desc[:100] + ("…" if len(desc) > 100 else "")
        lines += ["", short]

    # 詳細はリンクから
    lines += ["", f"👇 詳細はこちら", url, "", HASHTAG]

    text = "\n".join(lines)
    return text[:500]


def post_to_threads(text: str) -> str | None:
    """投稿成功時はpost_id、失敗時はNone"""
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not user_id or not token:
        print("[ERROR] THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定")
        return None

    base = "https://graph.threads.net/v1.0"
    r1 = requests.post(
        f"{base}/{user_id}/threads",
        params={"media_type": "TEXT", "text": text, "access_token": token},
        timeout=15,
    )
    if r1.status_code != 200:
        print(f"[ERROR] コンテナ作成失敗: {r1.status_code} {r1.text[:200]}")
        return None

    container_id = r1.json().get("id", "")
    time.sleep(3)

    r2 = requests.post(
        f"{base}/{user_id}/threads_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=15,
    )
    if r2.status_code == 200:
        post_id = r2.json().get("id", "")
        print(f"[OK] 投稿成功: {post_id}")
        return post_id
    print(f"[ERROR] 公開失敗: {r2.status_code} {r2.text[:200]}")
    return None


def main():
    dry_run = "--dry-run" in sys.argv
    new_files = get_new_post_files()

    if not new_files:
        print("[SKIP] 新着記事なし")
        return

    # 複数記事でも最も注目度の高い1件だけ投稿（連投防止）
    path = pick_best(new_files)
    print(f"[INFO] 投稿対象: {path.name}（{len(new_files)}件中1件選択）")

    fm   = parse_front_matter(path)
    url  = build_post_url(path)
    text = build_text(fm, url)

    print("=" * 50)
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    print("=" * 50)
    print(f"URL: {url}")

    if dry_run:
        print("[DRY-RUN] 投稿スキップ")
        return

    post_to_threads(text)


if __name__ == "__main__":
    main()
