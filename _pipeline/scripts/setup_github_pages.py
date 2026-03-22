"""
setup_github_pages.py: GitHub Pages の初回セットアップを対話的に実行する

やること:
  1. git の初期設定確認
  2. site/ ディレクトリを git リポジトリとして初期化
  3. GitHub にリポジトリを作成 (gh コマンド or 手動)
  4. 初回 push
  5. .env の GH_PAGES_REPO_URL を更新

使用方法:
  python scripts/setup_github_pages.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITE_DIR = ROOT / "site"

try:
    from dotenv import load_dotenv, set_key
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

sys.path.insert(0, str(ROOT))


def run(cmd, cwd=None, check=True, capture=False):
    result = subprocess.run(
        cmd, cwd=cwd or str(SITE_DIR),
        check=check, capture_output=capture, text=True, shell=False
    )
    return result.stdout.strip() if capture else None


def check_git_installed():
    try:
        v = subprocess.run(["git", "--version"], capture_output=True, text=True)
        print(f"✓ git: {v.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("✗ git が見つかりません。https://git-scm.com/ からインストールしてください。")
        return False


def check_git_config():
    name = subprocess.run(
        ["git", "config", "--global", "user.name"],
        capture_output=True, text=True
    ).stdout.strip()
    email = subprocess.run(
        ["git", "config", "--global", "user.email"],
        capture_output=True, text=True
    ).stdout.strip()

    if not name or not email:
        print("\n⚠ git のユーザー情報が未設定です。")
        name = input("  名前を入力 (例: Taro Yamada): ").strip()
        email = input("  メールを入力 (GitHubのアドレス推奨): ").strip()
        run(["git", "config", "--global", "user.name", name], cwd=str(ROOT))
        run(["git", "config", "--global", "user.email", email], cwd=str(ROOT))
        print("  ✓ git 設定完了")
    else:
        print(f"✓ git ユーザー: {name} <{email}>")


def init_site_repo():
    git_dir = SITE_DIR / ".git"
    if git_dir.exists():
        print("✓ site/ は既に git リポジトリです")
        return

    print("\n📁 site/ を git リポジトリとして初期化します...")
    run(["git", "init"])
    run(["git", "checkout", "-b", "main"])
    # 全ファイルを追加
    run(["git", "add", "."])
    run(["git", "commit", "-m", "Initial commit: Jekyll blog setup"])
    print("✓ 初期コミット完了")


def setup_remote():
    print("\n" + "="*50)
    print("GitHub リポジトリの設定")
    print("="*50)
    print("""
GitHub Pages のリポジトリを作成します。

【手順】
1. https://github.com/new にアクセス
2. Repository name に「あなたのユーザー名.github.io」と入力
   例: yamada-taro.github.io
3. Public を選択
4. 「Create repository」をクリック
5. 表示されたHTTPS URLをここに貼り付け
   例: https://github.com/yamada-taro/yamada-taro.github.io.git
""")

    repo_url = input("GitHub リポジトリの HTTPS URL: ").strip()
    if not repo_url:
        print("スキップします (後で手動で設定できます)")
        return None

    # リモート設定
    try:
        run(["git", "remote", "remove", "origin"], check=False)
    except Exception:
        pass
    run(["git", "remote", "add", "origin", repo_url])
    print(f"✓ リモート設定: {repo_url}")
    return repo_url


def push_to_github(repo_url):
    print("\n📤 GitHub に push します...")
    print("  (GitHub のユーザー名とパスワード/トークンを求められる場合があります)")
    print("  パスワードは Personal Access Token を使用してください")
    print("  取得方法: GitHub → Settings → Developer settings → Personal access tokens")
    print()

    try:
        run(["git", "push", "-u", "origin", "main"])
        print("✓ push 完了!")
        username = repo_url.split("/")[-2] if repo_url else ""
        repo_name = repo_url.split("/")[-1].replace(".git", "") if repo_url else ""
        print(f"\n🌐 サイトURL: https://{repo_name}/")
        print("  (反映まで数分かかります)")
        return True
    except subprocess.CalledProcessError:
        print("""
✗ push に失敗しました。以下を確認してください:

1. GitHub の Personal Access Token を使う場合:
   - GitHub → Settings → Developer settings → Personal access tokens → Generate new token
   - 権限: repo にチェック
   - パスワード欄にトークンを貼り付け

2. SSH キーを使う場合:
   - git remote set-url origin git@github.com:ユーザー名/リポジトリ名.git

3. GitHub CLI (gh) がある場合:
   - gh auth login
""")
        return False


def update_env(repo_url):
    """GH_PAGES_REPO_URL を .env に保存"""
    env_path = ROOT / ".env"
    try:
        set_key(str(env_path), "GH_PAGES_REPO_URL", repo_url)
        print(f"✓ .env の GH_PAGES_REPO_URL を更新しました")
    except Exception:
        print(f"  手動で .env に以下を追記してください:")
        print(f"  GH_PAGES_REPO_URL={repo_url}")


def main():
    print("="*50)
    print("GitHub Pages セットアップ")
    print("="*50)

    if not check_git_installed():
        sys.exit(1)

    check_git_config()
    init_site_repo()
    repo_url = setup_remote()

    if repo_url:
        success = push_to_github(repo_url)
        if success:
            update_env(repo_url)
            print("""
╔══════════════════════════════════════════╗
║  セットアップ完了！                      ║
║                                          ║
║  次のステップ:                           ║
║  1. サイトが表示されることを確認         ║
║  2. AdSense 審査に申請                   ║
║  3. タスクスケジューラを設定             ║
║     → python scripts/setup_scheduler.py ║
╚══════════════════════════════════════════╝
""")
    else:
        print("\n後で以下のコマンドで再実行できます:")
        print("  python scripts/setup_github_pages.py")


if __name__ == "__main__":
    main()
