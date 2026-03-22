"""
Logger: ロギング設定
"""
import logging
import logging.handlers
from pathlib import Path


def setup_logger(level: str = "INFO", log_file: str = "logs/pipeline.log"):
    """
    ルートロガーを設定する
    - コンソール: INFO以上をrichで表示
    - ファイル: DEBUGを含む全ログを保存 (10MB x 5世代)
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 既存ハンドラをクリア (二重登録防止)
    root_logger.handlers.clear()

    # コンソールハンドラ
    try:
        from rich.logging import RichHandler
        console_handler = RichHandler(
            level=numeric_level,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
        )
    except ImportError:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root_logger.addHandler(console_handler)

    # ファイルハンドラ (ローテーション)
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_path),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(file_handler)

    return root_logger
