"""
Threads エンゲージメント自動化スクリプト
- ハッシュタグ検索 → 投稿にいいね（最大10件/実行）
- ガジェット系アカウントをフォロー（最大3件/実行）
- 認証: THREADS_COOKIES_JSON シークレットに保存されたCookies

実行: python _pipeline/scripts/threads_engagement.py [--dry-run]
依存: playwright (pip install playwright && playwright install chromium)
"""

import json
import os
import random
import sys
import time
from pathlib import Path

ROOT         = Path(__file__).parent.parent
HISTORY_PATH = ROOT / "data" / "engagement_history.json"

# いいね対象ハッシュタグ（ローテーション）
TARGET_HASHTAGS = [
    "ガジェット", "イヤホン", "ワイヤレスイヤホン",
    "スマートホーム", "Amazonセール", "テック",
]

# フォロー候補ワード（プロフィール検索用）
FOLLOW_KEYWORDS = ["ガジェットレビュー", "テックブログ", "Amazon活用"]

LIKE_PER_RUN   = 10
FOLLOW_PER_RUN = 3


def load_history() -> dict:
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return {"liked": [], "followed": [], "hashtag_index": 0}


def save_history(h: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cookies() -> list:
    raw = os.environ.get("THREADS_COOKIES_JSON", "")
    if not raw:
        print("[ERROR] THREADS_COOKIES_JSON が未設定")
        sys.exit(1)
    return json.loads(raw)


def run(dry_run: bool):
    from playwright.sync_api import sync_playwright

    history  = load_history()
    cookies  = load_cookies()

    tag_idx  = history.get("hashtag_index", 0)
    tag      = TARGET_HASHTAGS[tag_idx % len(TARGET_HASHTAGS)]
    history["hashtag_index"] = tag_idx + 1

    liked_count   = 0
    followed_count = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        # ===== いいね =====
        print(f"[INFO] ハッシュタグ検索: #{tag}")
        page.goto(f"https://www.threads.com/search?q=%23{tag}&serp_type=default", timeout=20000)
        page.wait_for_timeout(3000)

        # いいねボタンを探してクリック
        like_buttons = page.query_selector_all('[aria-label="いいね"]')
        print(f"[INFO] いいねボタン検出: {len(like_buttons)}件")

        for btn in like_buttons[:LIKE_PER_RUN]:
            try:
                post_id = btn.get_attribute("data-testid") or str(id(btn))
                if post_id in history["liked"]:
                    continue
                if not dry_run:
                    btn.click()
                    time.sleep(random.uniform(1.5, 3.0))
                history["liked"].append(post_id)
                liked_count += 1
                print(f"[LIKE] {'(dry)' if dry_run else ''} {post_id[:30]}")
            except Exception as e:
                print(f"[WARN] いいね失敗: {e}")

        # liked履歴は最新1000件だけ保持
        history["liked"] = history["liked"][-1000:]

        # ===== フォロー =====
        kw = random.choice(FOLLOW_KEYWORDS)
        print(f"[INFO] フォロー候補検索: {kw}")
        page.goto(f"https://www.threads.com/search?q={kw}&serp_type=accounts", timeout=20000)
        page.wait_for_timeout(3000)

        follow_buttons = page.query_selector_all('[aria-label="フォローする"]')
        print(f"[INFO] フォローボタン検出: {len(follow_buttons)}件")

        for btn in follow_buttons[:FOLLOW_PER_RUN]:
            try:
                username = btn.get_attribute("data-username") or str(id(btn))
                if username in history["followed"]:
                    continue
                if not dry_run:
                    btn.click()
                    time.sleep(random.uniform(2.0, 4.0))
                history["followed"].append(username)
                followed_count += 1
                print(f"[FOLLOW] {'(dry)' if dry_run else ''} {username}")
            except Exception as e:
                print(f"[WARN] フォロー失敗: {e}")

        browser.close()

    print(f"[DONE] いいね: {liked_count}件 / フォロー: {followed_count}件")
    save_history(history)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run(dry_run)
