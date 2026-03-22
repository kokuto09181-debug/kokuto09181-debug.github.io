"""
JekyllPublisher: ProcessedArticleをJekyll _posts/*.md ファイルに書き出す
"""
import logging
from datetime import datetime
from pathlib import Path

from ..models.article import ProcessedArticle

logger = logging.getLogger(__name__)


class JekyllPublisher:
    """ProcessedArticleをJekyllの_postsディレクトリにMarkdownとして書き出す"""

    def __init__(self, posts_dir: str):
        self.posts_dir = Path(posts_dir)
        self.posts_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, article: ProcessedArticle) -> bool:
        """
        記事を_postsディレクトリに書き出す

        Returns:
            成功した場合はTrue
        """
        try:
            filepath = self._get_filepath(article)
            content = self._build_content(article)

            filepath.write_text(content, encoding="utf-8")
            article.is_published = True
            logger.info(f"[Jekyll] 書き出し完了: {filepath.name}")
            return True
        except Exception as e:
            logger.error(f"[Jekyll] 書き出し失敗: {e}")
            return False

    def publish_batch(self, articles: list[ProcessedArticle]) -> int:
        """複数記事を書き出す。成功数を返す"""
        count = 0
        for article in articles:
            if self.publish(article):
                count += 1
        logger.info(f"[Jekyll] {count}/{len(articles)}件 書き出し完了")
        return count

    def _get_filepath(self, article: ProcessedArticle) -> Path:
        """ファイルパスを生成 (衝突時はカウンタ付加)"""
        date_str = article.published_at.strftime("%Y-%m-%d")
        base_name = f"{date_str}-{article.slug}"[:80]  # ファイル名長さ制限
        filepath = self.posts_dir / f"{base_name}.md"

        # 衝突回避
        counter = 1
        while filepath.exists():
            filepath = self.posts_dir / f"{base_name}-{counter}.md"
            counter += 1

        return filepath

    def _build_content(self, article: ProcessedArticle) -> str:
        """Jekyllファイルの内容を構築"""
        frontmatter = article.to_jekyll_frontmatter()

        # アイキャッチ画像はpost.htmlのレイアウト側で表示するため本文には含めない
        # 2枚目以降の画像をH2セクション間に自然に挿入する
        body = self._inject_images(article)

        source_footer = f"""

---

**参考元**: [{article.source_item.source}]({article.source_item.url})
"""
        return frontmatter + "\n" + body + "\n" + source_footer

    def _inject_images(self, article: ProcessedArticle) -> str:
        """
        本文のH2セクション間に元記事の画像を挿入する
        1枚目はpost.htmlのアイキャッチとして使用済みなので2枚目から挿入
        """
        body = article.ja_body
        images = article.source_item.image_urls or []

        # thumbnail_urlも含めて重複排除済みリストを作成し、2枚目以降を使う
        thumbnail = article.source_item.thumbnail_url or ""
        extra_images = [u for u in images if u != thumbnail]

        if not extra_images:
            return body

        # H2見出しで本文を分割してセクションごとに画像を挿入
        import re
        sections = re.split(r'(\n## )', body)
        if len(sections) <= 1:
            # H2がない場合は末尾にまとめて付加
            img_block = "\n\n" + "\n\n".join(
                f'![画像{i+1}]({u})' for i, u in enumerate(extra_images[:3])
            )
            return body + img_block

        result = [sections[0]]
        img_idx = 0
        for i in range(1, len(sections), 2):
            sep = sections[i]       # "\n## "
            content = sections[i + 1] if i + 1 < len(sections) else ""
            result.append(sep + content)
            # 1セクションおきに画像を挿入
            if img_idx < len(extra_images) and i % 4 == 1:
                result.append(f'\n\n![関連画像]({extra_images[img_idx]})\n')
                img_idx += 1

        return "".join(result)
