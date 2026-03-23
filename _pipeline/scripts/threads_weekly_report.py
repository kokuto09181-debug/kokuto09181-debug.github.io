"""
Threads 週次パフォーマンスレポート
- 過去7日間の投稿メトリクスを集計
- _pipeline/data/reports/YYYY-WW.md に保存
- 実行: python _pipeline/scripts/threads_weekly_report.py
"""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT         = Path(__file__).parent.parent
REPORTS_DIR  = ROOT / "data" / "reports"

JST = timezone(timedelta(hours=9))


def threads_get(path: str, params: dict) -> dict:
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not user_id or not token:
        print("[ERROR] THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定")
        sys.exit(1)

    base = "https://graph.threads.net/v1.0"
    url  = f"{base}/{path.format(user_id=user_id)}"
    params["access_token"] = token
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        print(f"[ERROR] API失敗 {r.status_code}: {r.text[:200]}")
        return {}
    return r.json()


def fetch_recent_posts(days: int = 7) -> list[dict]:
    """直近N日の投稿を取得"""
    data = threads_get(
        "{user_id}/threads",
        {
            "fields": "id,text,timestamp,like_count,replies_count,views,reposts_count,quotes_count",
            "limit": 100,
        },
    )
    posts = data.get("data", [])

    cutoff = datetime.now(JST) - timedelta(days=days)
    recent = []
    for p in posts:
        ts_str = p.get("timestamp", "")
        if not ts_str:
            continue
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(JST)
        if ts >= cutoff:
            recent.append({**p, "ts": ts})
    return recent


def fetch_account_insights() -> dict:
    """アカウント全体のインサイト（フォロワー数等）"""
    data = threads_get(
        "{user_id}/threads_publishing_limit",
        {"fields": "config,quota_usage"},
    )
    # フォロワー数は別エンドポイント
    followers_data = threads_get(
        "{user_id}",
        {"fields": "id,username,threads_profile_picture_url,followers_count"},
    )
    return {
        "followers_count": followers_data.get("followers_count", "N/A"),
        "username":        followers_data.get("username", ""),
    }


def format_report(posts: list[dict], account: dict, week_str: str) -> str:
    total_views   = sum(p.get("views", 0) or 0 for p in posts)
    total_likes   = sum(p.get("like_count", 0) or 0 for p in posts)
    total_replies = sum(p.get("replies_count", 0) or 0 for p in posts)
    total_reposts = sum(p.get("reposts_count", 0) or 0 for p in posts)

    avg_views  = total_views  // len(posts) if posts else 0
    avg_likes  = total_likes  // len(posts) if posts else 0

    top_posts = sorted(posts, key=lambda p: p.get("views", 0) or 0, reverse=True)[:3]

    lines = [
        f"# Threads 週次レポート {week_str}",
        "",
        f"生成日時: {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}",
        "",
        "## サマリー",
        "",
        f"| 指標 | 値 |",
        f"|---|---|",
        f"| フォロワー数 | {account.get('followers_count', 'N/A')} |",
        f"| 投稿数（7日） | {len(posts)} |",
        f"| 総ビュー数 | {total_views:,} |",
        f"| 総いいね数 | {total_likes:,} |",
        f"| 総リプライ数 | {total_replies:,} |",
        f"| 総リポスト数 | {total_reposts:,} |",
        f"| 平均ビュー/投稿 | {avg_views:,} |",
        f"| 平均いいね/投稿 | {avg_likes:,} |",
        "",
        "## 上位投稿（ビュー数）",
        "",
    ]

    for i, p in enumerate(top_posts, 1):
        text_preview = (p.get("text") or "")[:60].replace("\n", " ")
        ts = p["ts"].strftime("%m/%d %H:%M") if "ts" in p else ""
        lines += [
            f"### {i}位 ({ts})",
            f"> {text_preview}…",
            f"",
            f"- ビュー: {p.get('views', 0):,}",
            f"- いいね: {p.get('like_count', 0):,}",
            f"- リプライ: {p.get('replies_count', 0):,}",
            "",
        ]

    lines += [
        "## 全投稿一覧",
        "",
        "| 日時 | ビュー | いいね | リプライ | 本文（60文字）|",
        "|---|---|---|---|---|",
    ]
    for p in sorted(posts, key=lambda p: p.get("ts", datetime.min.replace(tzinfo=JST)), reverse=True):
        ts = p["ts"].strftime("%m/%d %H:%M") if "ts" in p else "-"
        text_preview = (p.get("text") or "")[:60].replace("|", "｜").replace("\n", " ")
        lines.append(
            f"| {ts} | {p.get('views',0):,} | {p.get('like_count',0):,} "
            f"| {p.get('replies_count',0):,} | {text_preview} |"
        )

    return "\n".join(lines) + "\n"


def main():
    today    = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    week_str = f"{iso_year}-W{iso_week:02d}"

    print(f"[INFO] レポート生成: {week_str}")

    posts   = fetch_recent_posts(days=7)
    account = fetch_account_insights()

    print(f"[INFO] 取得投稿数: {len(posts)}")
    print(f"[INFO] フォロワー数: {account.get('followers_count', 'N/A')}")

    report = format_report(posts, account, week_str)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{week_str}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"[OK] レポート保存: {out_path}")

    # stdout にも出力（GitHub Actions ログ）
    sys.stdout.buffer.write(report.encode("utf-8"))


if __name__ == "__main__":
    main()
