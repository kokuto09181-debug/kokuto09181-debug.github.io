"""
スラッグ生成: 日本語タイトルから英数字URLスラッグを生成する
"""
import re
import unicodedata
from datetime import datetime


def generate_slug(title: str) -> str:
    """
    日本語タイトルからJekyll用スラッグを生成する

    戦略:
    1. ASCIIに変換できる部分はそのまま使用
    2. 日本語部分はunicode正規化してASCII以外を除去
    3. 最終的にタイムスタンプを付加して一意性を確保
    """
    # Unicode正規化 (NFKD: 全角→半角など)
    normalized = unicodedata.normalize("NFKD", title)

    # ASCII変換可能な文字を残す
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # 小文字化
    slug = ascii_text.lower()

    # 英数字とスペース以外を除去
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)

    # 空白をハイフンに変換
    slug = re.sub(r"[\s-]+", "-", slug)

    # 先頭末尾のハイフン除去
    slug = slug.strip("-")

    # 短すぎる場合(日本語タイトルでASCIIが全部消えた場合)はtimestampのみ
    if len(slug) < 3:
        slug = "article"

    # 最大50文字
    slug = slug[:50].rstrip("-")

    # タイムスタンプを付加して一意性確保
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{slug}-{ts}"
