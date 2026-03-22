"""
GitPublisher: siteディレクトリをgit add/commit/pushしてGitHub Pagesにデプロイ
"""
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class GitPublisher:
    """Gitを使ってGitHub Pagesにデプロイする"""

    def __init__(self, site_dir: str, branch: str = "main", dry_run: bool = True):
        self.site_dir = Path(site_dir)
        self.branch = branch
        self.dry_run = dry_run

    def _get_auth_remote_url(self) -> str | None:
        """GH_TOKENが設定されていればトークン付きURLを返す"""
        token = os.environ.get("GH_TOKEN", "")
        repo_url = os.environ.get("GH_PAGES_REPO_URL", "")
        if token and repo_url and repo_url.startswith("https://"):
            # https://TOKEN@github.com/... 形式に変換
            return repo_url.replace("https://", f"https://{token}@", 1)
        return None

    def deploy(self, article_count: int) -> bool:
        """
        変更をコミットしてpushする

        Args:
            article_count: 今回追加した記事数

        Returns:
            成功した場合はTrue
        """
        if self.dry_run:
            logger.info("[Git] dry_run=True のためpushをスキップ")
            return True

        try:
            # トークン付きURLでリモートを更新
            auth_url = self._get_auth_remote_url()
            if auth_url:
                self._run(["git", "remote", "set-url", "origin", auth_url])

            # git add
            self._run(["git", "add", "_posts/"])

            # 変更がなければスキップ
            status = self._run(
                ["git", "status", "--porcelain"],
                capture=True
            )
            if not status.strip():
                logger.info("[Git] コミットする変更がありません")
                return True

            # git commit
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = f"Add {article_count} new articles [{date_str}]"
            self._run(["git", "commit", "-m", message])

            # git push
            self._run(["git", "push", "origin", self.branch])
            logger.info(f"[Git] push完了: {message}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"[Git] コマンド失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"[Git] エラー: {e}")
            return False

    def _run(self, cmd: list[str], capture: bool = False) -> str:
        """コマンドを site_dir で実行"""
        result = subprocess.run(
            cmd,
            cwd=str(self.site_dir),
            check=True,
            capture_output=capture,
            text=True
        )
        return result.stdout if capture else ""

    def init_repo(self, remote_url: str):
        """
        GitHub Pages用リポジトリを初期化する (初回セットアップ時のみ)
        """
        if (self.site_dir / ".git").exists():
            logger.info("[Git] リポジトリ既に存在します")
            return

        cmds = [
            ["git", "init"],
            ["git", "checkout", "-b", "main"],
            ["git", "remote", "add", "origin", remote_url],
        ]
        for cmd in cmds:
            self._run(cmd)
        logger.info(f"[Git] リポジトリ初期化完了: {remote_url}")
