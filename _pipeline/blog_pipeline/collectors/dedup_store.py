"""
DedupStore: SQLiteベースのURL重複チェック
同じ記事を2回処理しないようにするためのシンプルなストア
"""
import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "seen_urls.db"


class DedupStore:
    """URLの重複チェックをSQLiteで管理する"""

    def __init__(self, db_path: Path = DB_PATH, ttl_days: int = 30):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_urls (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    seen_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_seen_at ON seen_urls(seen_at)
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    @staticmethod
    def _hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def is_seen(self, url: str) -> bool:
        """URLが既に処理済みかチェック"""
        url_hash = self._hash(url)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_urls WHERE url_hash = ?",
                (url_hash,)
            ).fetchone()
        return row is not None

    def mark_seen(self, url: str):
        """URLを処理済みとしてマーク"""
        url_hash = self._hash(url)
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seen_urls (url_hash, url, seen_at) VALUES (?, ?, ?)",
                (url_hash, url, now)
            )

    def filter_new(self, items) -> list:
        """FeedItemリストから未処理のものだけを返す"""
        new_items = []
        for item in items:
            if not self.is_seen(item.url):
                new_items.append(item)
        logger.info(
            f"[Dedup] {len(items)}件中 {len(new_items)}件が新規"
        )
        return new_items

    def cleanup_old(self):
        """TTL期限切れのURLを削除"""
        cutoff = (datetime.utcnow() - timedelta(days=self.ttl_days)).isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM seen_urls WHERE seen_at < ?",
                (cutoff,)
            )
            if cursor.rowcount > 0:
                logger.info(f"[Dedup] {cursor.rowcount}件の古いURLを削除")
