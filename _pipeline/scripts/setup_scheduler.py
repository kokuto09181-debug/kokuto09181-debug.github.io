"""
setup_scheduler.py: Windowsタスクスケジューラにパイプラインを登録する

実行すると毎日6時・18時に run_pipeline.bat が自動実行されます。
管理者権限は不要です (ユーザータスクとして登録)。

使用方法:
  python scripts/setup_scheduler.py          # タスク登録
  python scripts/setup_scheduler.py --remove # タスク削除
  python scripts/setup_scheduler.py --status # 登録状況確認
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BAT_FILE = ROOT / "run_pipeline.bat"
TASK_NAME = "GadgetBlogPipeline"


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.returncode, result.stdout, result.stderr


def register_task():
    """タスクスケジューラに朝6時・夜18時の実行を登録"""
    print(f"タスク「{TASK_NAME}」を登録します...")

    # 既存タスクを削除
    run(f'schtasks /delete /tn "{TASK_NAME}_Morning" /f')
    run(f'schtasks /delete /tn "{TASK_NAME}_Evening" /f')

    bat_path = str(BAT_FILE).replace("/", "\\")

    # 朝6時のタスク
    cmd_morning = (
        f'schtasks /create /tn "{TASK_NAME}_Morning" '
        f'/tr "cmd /c \"{bat_path}\"" '
        f'/sc DAILY /st 06:00 '
        f'/f /rl LIMITED'
    )
    code, out, err = run(cmd_morning)
    if code == 0:
        print("✓ 朝6時のタスク登録完了")
    else:
        print(f"✗ 朝6時のタスク登録失敗: {err}")

    # 夜18時のタスク
    cmd_evening = (
        f'schtasks /create /tn "{TASK_NAME}_Evening" '
        f'/tr "cmd /c \"{bat_path}\"" '
        f'/sc DAILY /st 18:00 '
        f'/f /rl LIMITED'
    )
    code, out, err = run(cmd_evening)
    if code == 0:
        print("✓ 夜18時のタスク登録完了")
    else:
        print(f"✗ 夜18時のタスク登録失敗: {err}")

    print(f"""
登録完了！

確認方法:
  タスクスケジューラを開く → 「{TASK_NAME}_Morning」「{TASK_NAME}_Evening」を確認
  または: python scripts/setup_scheduler.py --status

手動テスト実行:
  schtasks /run /tn "{TASK_NAME}_Morning"
""")


def remove_task():
    """タスクを削除"""
    for suffix in ["_Morning", "_Evening"]:
        code, out, err = run(f'schtasks /delete /tn "{TASK_NAME}{suffix}" /f')
        if code == 0:
            print(f"✓ {TASK_NAME}{suffix} を削除しました")
        else:
            print(f"  {TASK_NAME}{suffix} は未登録でした")


def show_status():
    """登録状況を表示"""
    print("=== タスクスケジューラ 登録状況 ===\n")
    for suffix in ["_Morning", "_Evening"]:
        code, out, err = run(f'schtasks /query /tn "{TASK_NAME}{suffix}" /fo LIST')
        if code == 0:
            # 必要な行だけ抽出
            for line in out.splitlines():
                if any(k in line for k in ["タスク名", "Task Name", "状態", "Status",
                                            "次の実行", "Next Run", "最後の実行", "Last Run"]):
                    print(line)
            print()
        else:
            print(f"✗ {TASK_NAME}{suffix} は未登録です")


def main():
    parser = argparse.ArgumentParser(description="Windowsタスクスケジューラ設定")
    parser.add_argument("--remove", action="store_true", help="タスクを削除")
    parser.add_argument("--status", action="store_true", help="登録状況を確認")
    args = parser.parse_args()

    if not BAT_FILE.exists():
        print(f"✗ バッチファイルが見つかりません: {BAT_FILE}")
        sys.exit(1)

    if args.remove:
        remove_task()
    elif args.status:
        show_status()
    else:
        register_task()


if __name__ == "__main__":
    main()
