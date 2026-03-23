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

TARGET_HASHTAGS = [
    "ガジェット", "イヤホン", "ワイヤレスイヤホン",
    "スマートホーム", "Amazonセール", "テック",
]
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
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[ERROR] THREADS_COOKIES_JSON のJSON解析失敗: {e}")
        sys.exit(1)


def run_dry():
    """dry-run: Playwright不使用。スケジュール・設定の確認のみ"""
    history = load_history()
    tag_idx = history.get("hashtag_index", 0)
    tag     = TARGET_HASHTAGS[tag_idx % len(TARGET_HASHTAGS)]
    kw      = random.choice(FOLLOW_KEYWORDS)

    print("[DRY-RUN] エンゲージメント設定確認")
    print(f"  今回のいいね対象ハッシュタグ: #{tag}")
    print(f"  今回のフォロー候補キーワード: {kw}")
    print(f"  いいね上限: {LIKE_PER_RUN}件/回")
    print(f"  フォロー上限: {FOLLOW_PER_RUN}件/回")
    print(f"  履歴: いいね済み{len(history['liked'])}件 / フォロー済み{len(history['followed'])}件")
    print("[DRY-RUN] 実際のブラウザ操作はスキップしました")


def run_live():
    from playwright.sync_api import sync_playwright

    history = load_history()
    cookies = load_cookies()

    tag_idx = history.get("hashtag_index", 0)
    tag     = TARGET_HASHTAGS[tag_idx % len(TARGET_HASHTAGS)]
    history["hashtag_index"] = tag_idx + 1

    liked_count    = 0
    followed_count = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Mobile Safari/537.36"
            ),
            viewport={"width": 390, "height": 844},
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        # ===== いいね =====
        print(f"[INFO] ハッシュタグ: #{tag}")
        try:
            page.goto(
                f"https://www.threads.com/search?q=%23{tag}&serp_type=default",
                timeout=30000,
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(4000)

            # いいねボタン候補（aria-labelは日英両方試す）
            selectors = [
                '[aria-label="いいね"]',
                '[aria-label="Like"]',
                'svg[aria-label="いいね"]',
                'svg[aria-label="Like"]',
            ]
            like_buttons = []
            for sel in selectors:
                btns = page.query_selector_all(sel)
                if btns:
                    like_buttons = btns
                    print(f"[INFO] セレクタ '{sel}' で{len(btns)}件検出")
                    break

            if not like_buttons:
                print("[WARN] いいねボタンが見つかりませんでした（ログイン失敗またはUI変更の可能性）")
            else:
                for btn in like_buttons[:LIKE_PER_RUN]:
                    try:
                        post_id = str(abs(hash(btn.get_attribute("class") or "")))[:16]
                        if post_id in history["liked"]:
                            continue
                        btn.click()
                        time.sleep(random.uniform(1.5, 3.0))
                        history["liked"].append(post_id)
                        liked_count += 1
                        print(f"[LIKE] {liked_count}件目")
                    except Exception as e:
                        print(f"[WARN] いいね失敗: {e}")

        except Exception as e:
            print(f"[WARN] ハッシュタグ検索エラー: {e}")

        history["liked"] = history["liked"][-1000:]

        # ===== フォロー =====
        kw = random.choice(FOLLOW_KEYWORDS)
        print(f"[INFO] フォロー候補: {kw}")
        try:
            page.goto(
                f"https://www.threads.com/search?q={kw}&serp_type=accounts",
                timeout=30000,
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(4000)

            follow_selectors = [
                '[aria-label="フォローする"]',
                '[aria-label="Follow"]',
            ]
            follow_buttons = []
            for sel in follow_selectors:
                btns = page.query_selector_all(sel)
                if btns:
                    follow_buttons = btns
                    break

            for btn in follow_buttons[:FOLLOW_PER_RUN]:
                try:
                    uid = str(abs(hash(btn.get_attribute("class") or "")))[:16]
                    if uid in history["followed"]:
                        continue
                    btn.click()
                    time.sleep(random.uniform(2.0, 4.0))
                    history["followed"].append(uid)
                    followed_count += 1
                    print(f"[FOLLOW] {followed_count}件目")
                except Exception as e:
                    print(f"[WARN] フォロー失敗: {e}")

        except Exception as e:
            print(f"[WARN] フォロー検索エラー: {e}")

        browser.close()

    print(f"[DONE] いいね: {liked_count}件 / フォロー: {followed_count}件")
    save_history(history)


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        run_dry()
    else:
        run_live()
