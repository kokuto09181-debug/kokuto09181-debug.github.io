"""
Threads フェッチャー
投稿から24時間以上経過した記事のメトリクス（閲覧数・いいね等）を取得してログに保存
実行: python _pipeline/scripts/threads_fetcher.py
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT           = Path(__file__).parent.parent
POSTS_LOG_PATH = ROOT / "data" / "threads_posts_log.json"
METRICS_FIELDS = "views,likes,replies,reposts,quotes"
FETCH_DELAY_H  = 24   # 投稿後何時間で取得するか


def load_posts_log() -> list:
    if POSTS_LOG_PATH.exists():
        with open(POSTS_LOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts_log(posts_log: list):
    with open(POSTS_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(posts_log, f, ensure_ascii=False, indent=2)


def fetch_metrics(post_id: str, token: str) -> dict | None:
    """Threads Insights APIで1投稿のメトリクスを取得"""
    base = "https://graph.threads.net/v1.0"
    r = requests.get(
        f"{base}/{post_id}/insights",
        params={"metric": METRICS_FIELDS, "access_token": token},
        timeout=10,
    )
    if r.status_code != 200:
        print(f"[WARN] {post_id} metrics失敗: {r.status_code} {r.text[:100]}", flush=True)
        return None

    result = {}
    for item in r.json().get("data", []):
        name = item.get("name", "")
        # Threads APIは total_value.value 形式
        val = item.get("total_value", {}).get("value", 0)
        result[name] = val

    return result if result else None


def main():
    token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not token:
        print("[ERROR] THREADS_ACCESS_TOKEN 未設定", flush=True)
        sys.exit(1)

    posts_log = load_posts_log()
    if not posts_log:
        print("[SKIP] ログが空です", flush=True)
        return

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=FETCH_DELAY_H)

    targets = [
        p for p in posts_log
        if p.get("post_id")
        and not p.get("metrics")
        and datetime.fromisoformat(p["posted_at"]).astimezone(timezone.utc) < cutoff
    ]

    print(f"[INFO] メトリクス取得対象: {len(targets)}件", flush=True)

    updated = 0
    for entry in targets:
        metrics = fetch_metrics(entry["post_id"], token)
        if metrics:
            entry["metrics"] = metrics
            entry["metrics_fetched_at"] = now.isoformat()
            eng = metrics.get("likes", 0) + metrics.get("replies", 0) + metrics.get("reposts", 0)
            views = max(metrics.get("views", 1), 1)
            rate = round(eng / views * 100, 2)
            print(
                f"[OK] {entry['post_id']} [{entry['category']}] "
                f"views={metrics.get('views',0)} likes={metrics.get('likes',0)} "
                f"eng_rate={rate}%",
                flush=True,
            )
            updated += 1
        time.sleep(0.5)

    if updated:
        save_posts_log(posts_log)

    print(f"[DONE] {updated}/{len(targets)}件 更新完了", flush=True)


if __name__ == "__main__":
    main()
