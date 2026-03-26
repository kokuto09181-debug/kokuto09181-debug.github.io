"""
Threads アナリスト
posts_log.json を分析してカテゴリ別パフォーマンスを計算し
post_weights.json を生成する（次回投稿の確率調整に使用）
実行: python _pipeline/scripts/threads_analyst.py
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT           = Path(__file__).parent.parent
POSTS_LOG_PATH = ROOT / "data" / "threads_posts_log.json"
WEIGHTS_PATH   = ROOT / "data" / "post_weights.json"
REPORT_PATH    = ROOT / "data" / "analytics_report.json"

MIN_SAMPLES = 3   # 分析に最低必要なサンプル数（これ未満のカテゴリは重み1.0のまま）


def load_posts_log() -> list:
    if POSTS_LOG_PATH.exists():
        with open(POSTS_LOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def calc_engagement_rate(metrics: dict) -> float:
    views = max(metrics.get("views", 0), 1)
    eng   = metrics.get("likes", 0) + metrics.get("replies", 0) + metrics.get("reposts", 0)
    return eng / views * 100


def analyze(posts_log: list) -> dict:
    """カテゴリ別・時間帯別のパフォーマンスを集計"""
    # メトリクスが取得済みの投稿のみ対象
    measured = [p for p in posts_log if p.get("metrics")]
    if not measured:
        return {}

    # カテゴリ別集計
    by_cat = defaultdict(list)
    by_hour = defaultdict(list)
    for p in measured:
        rate = calc_engagement_rate(p["metrics"])
        views = p["metrics"].get("views", 0)
        by_cat[p["category"]].append({"rate": rate, "views": views})
        by_hour[p.get("hour", 0)].append({"rate": rate, "views": views})

    # カテゴリ別平均
    cat_stats = {}
    for cat, items in by_cat.items():
        avg_rate  = sum(i["rate"]  for i in items) / len(items)
        avg_views = sum(i["views"] for i in items) / len(items)
        cat_stats[cat] = {
            "avg_engagement_rate": round(avg_rate, 3),
            "avg_views":           round(avg_views, 1),
            "samples":             len(items),
        }

    # 時間帯別平均
    hour_stats = {}
    for hour, items in by_hour.items():
        avg_views = sum(i["views"] for i in items) / len(items)
        hour_stats[str(hour)] = {
            "avg_views": round(avg_views, 1),
            "samples":   len(items),
        }

    return {"cat_stats": cat_stats, "hour_stats": hour_stats, "total_measured": len(measured)}


def calc_weights(cat_stats: dict) -> dict:
    """
    エンゲージメント率に基づいてカテゴリ重みを計算
    全カテゴリの平均を1.0として相対値を出す
    サンプル不足のカテゴリは1.0のまま
    """
    eligible = {
        cat: s for cat, s in cat_stats.items()
        if s["samples"] >= MIN_SAMPLES
    }
    if not eligible:
        return {}

    avg_rate = sum(s["avg_engagement_rate"] for s in eligible.values()) / len(eligible)
    if avg_rate == 0:
        return {}

    weights = {}
    for cat, s in eligible.items():
        raw = s["avg_engagement_rate"] / avg_rate
        # 重みは 0.3〜2.5 にクランプして極端な偏りを防ぐ
        weights[cat] = round(max(0.3, min(2.5, raw)), 3)

    return weights


def best_hours(hour_stats: dict, top_n: int = 4) -> list[int]:
    """平均閲覧数が高い上位N時間帯を返す"""
    eligible = {
        int(h): s for h, s in hour_stats.items()
        if s["samples"] >= 2
    }
    if not eligible:
        return []
    ranked = sorted(eligible, key=lambda h: eligible[h]["avg_views"], reverse=True)
    return ranked[:top_n]


def main():
    posts_log = load_posts_log()
    stats = analyze(posts_log)

    if not stats:
        print("[SKIP] メトリクス取得済み投稿がまだありません（フェッチャーを先に実行してください）", flush=True)
        return

    cat_stats  = stats["cat_stats"]
    hour_stats = stats["hour_stats"]
    weights    = calc_weights(cat_stats)
    top_hours  = best_hours(hour_stats)

    # post_weights.json を出力（threads_post.py が読み込む）
    output = {
        "category_weights": weights,
        "best_hours":       top_hours,
        "total_analyzed":   stats["total_measured"],
        "generated_at":     datetime.now(timezone.utc).isoformat(),
    }
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # analytics_report.json（人間が確認用）
    report = {
        "summary":     stats,
        "weights":     output,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # コンソールに要約を出力
    print("=" * 50, flush=True)
    print(f"[ANALYST] 分析完了 ({stats['total_measured']}件)", flush=True)
    print("--- カテゴリ別パフォーマンス ---", flush=True)
    for cat, s in sorted(cat_stats.items(), key=lambda x: -x[1]["avg_engagement_rate"]):
        w = weights.get(cat, 1.0)
        marker = "↑" if w > 1.1 else ("↓" if w < 0.9 else "→")
        print(
            f"  {marker} {cat:20s} eng={s['avg_engagement_rate']:.2f}% "
            f"views={s['avg_views']:.0f} n={s['samples']} weight={w}",
            flush=True,
        )
    if top_hours:
        print(f"--- 最適投稿時間帯: {top_hours} ---", flush=True)
    print("=" * 50, flush=True)


if __name__ == "__main__":
    main()
