"""
ローカルPC常時稼働デーモン
GitHub Actionsの代わりにノートPCで全ジョブを自動実行する

使い方:
  pip install schedule
  python _pipeline/scripts/run_local.py

特徴:
- 投稿スケジュールをここで一元管理（cron不要）
- セール期間を自動検出してスロット数を切り替え
- 深夜にフェッチャー+アナリストを自動実行
- Ctrl+C で安全に停止
"""
import subprocess
import sys
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import schedule
import time

ROOT       = Path(__file__).parent.parent.parent  # site/
SCRIPT_DIR = ROOT / "_pipeline" / "scripts"
LOG_PATH   = ROOT / "_pipeline" / "data" / "daemon.log"

JST = timezone(timedelta(hours=9))

SALE_START = date(2026, 3, 28)
SALE_END   = date(2026, 4, 2)

# ロギング設定
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def run_script(script_name: str, args: list[str] = None):
    """スクリプトを実行してログに出力"""
    args = args or []
    cmd = [sys.executable, str(SCRIPT_DIR / script_name)] + args
    log.info(f"▶ {script_name} {' '.join(args)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log.info(f"  {line}")
        if result.returncode != 0:
            log.error(f"  exit code {result.returncode}")
            if result.stderr:
                log.error(f"  {result.stderr[:300]}")
    except Exception as e:
        log.error(f"  実行エラー: {e}")


def job_post():
    """通常投稿ジョブ"""
    today = date.today()
    is_sale  = SALE_START <= today <= SALE_END
    pre_sale = (SALE_START - today).days <= 3 and today < SALE_START
    now_hour = datetime.now(JST).hour

    # 通常期: 8時・19時のみ有効
    normal_hours = {8, 19}
    sale_hours   = {7, 8, 10, 12, 15, 18, 19, 21}

    if is_sale or pre_sale:
        allowed = sale_hours
    else:
        allowed = normal_hours

    if now_hour not in allowed:
        log.info(f"[SKIP] JST {now_hour}時 は現在の期間では投稿なし")
        return

    run_script("threads_post.py")


def job_analytics():
    """深夜分析ジョブ（フェッチャー → アナリスト）"""
    log.info("=== 深夜分析開始 ===")
    run_script("threads_fetcher.py")
    run_script("threads_analyst.py")
    log.info("=== 分析完了 ===")


def job_engagement():
    """エンゲージメントジョブ（いいね・フォロー）"""
    run_script("threads_engagement.py")


def setup_schedule():
    """スケジュール登録"""
    # 投稿: 1時間ごとにチェック、job_post内でスキップ判定
    for h in range(7, 22):
        schedule.every().day.at(f"{h:02d}:05").do(job_post)

    # 分析: 毎日深夜2:10
    schedule.every().day.at("02:10").do(job_analytics)

    # エンゲージメント: 毎日11:00
    schedule.every().day.at("11:00").do(job_engagement)

    log.info("スケジュール登録完了")
    log.info("  投稿: 7〜21時の各:05 （セール判定で自動スキップ）")
    log.info("  分析: 毎日 02:10")
    log.info("  エンゲージメント: 毎日 11:00")


def main():
    log.info("=" * 50)
    log.info("Threads デーモン起動")
    log.info(f"セール期間: {SALE_START} 〜 {SALE_END}")
    today = date.today()
    if SALE_START <= today <= SALE_END:
        log.info("★ セール期間中 - 高頻度投稿モード")
    log.info("=" * 50)

    setup_schedule()

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("デーモン停止（Ctrl+C）")


if __name__ == "__main__":
    main()
