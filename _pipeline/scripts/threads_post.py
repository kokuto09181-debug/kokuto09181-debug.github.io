"""
Threads 自動投稿スクリプト（GitHub Actions用）
- LLM不使用: テンプレートYAMLから選択してデータを埋め込む
- post_history.json をリポジトリに保存して重複防止
- 実行: python _pipeline/scripts/threads_post.py [--dry-run]
"""

import json
import os
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
import yaml

# ===== パス =====
ROOT           = Path(__file__).parent.parent          # _pipeline/
TEMPLATES_PATH = ROOT / "config" / "threads_templates.yaml"
HISTORY_PATH   = ROOT / "data"  / "threads_post_history.json"

SALE_START = date(2026, 3, 28)
SALE_END   = date(2026, 4, 2)
BLOG_URL   = "https://gadgetpost.uk/sale/amazon-spring-2026/"

# ===== ハッシュタグ（Threads仕様: 1投稿1タグのみ有効）=====
_AUDIO_KEYS = {"airpods_pro3", "sony_wf_xm6", "sony_wh_xm6", "liberty4nc", "jbl_charge5"}

def _build_hashtags(category: str, product: dict = None) -> str:
    today = date.today()
    is_sale  = SALE_START <= today <= SALE_END
    pre_sale = (SALE_START - today) <= timedelta(days=3) and today < SALE_START

    if is_sale or pre_sale or category in ("sale_product", "sale_countdown", "pre_sale"):
        return "#Amazonセール"
    if category == "point_tips":
        return "#お得情報"
    if category == "follow":
        return "#ガジェット好きと繋がりたい"
    if product and product.get("key") in _AUDIO_KEYS:
        return "#イヤホン"
    return "#ガジェット"

# ===== 商品データ（静的・LLM不要）=====
_IMG = "https://m.media-amazon.com/images/I/{}"
PRODUCTS = [
    {"key": "airpods_pro3",  "asin": "B0FQFQDN6K", "name": "AirPods Pro 3",
     "price": "37,165円", "sale_price": "32,800円", "off": "12%", "effective": "約30,340円",
     "image_url": _IMG.format("61kX%2BMI8wvL._AC_SL500_.jpg")},
    {"key": "sony_wf_xm6",   "asin": "B0GL7VS33K", "name": "Sony WF-1000XM6",
     "price": "45,000円", "sale_price": "38,000円", "off": "16%", "effective": "約35,150円",
     "image_url": _IMG.format("41UmnBEDhpL._AC_SL500_.jpg")},
    {"key": "sony_wh_xm6",   "asin": "B0F77PMC1P", "name": "Sony WH-1000XM6",
     "price": "59,192円", "sale_price": "52,000円", "off": "12%", "effective": "約48,100円",
     "image_url": _IMG.format("41aRyTb8uPL._AC_SL500_.jpg")},
    {"key": "liberty4nc",    "asin": "B0C1P1N98V", "name": "Soundcore Liberty 4 NC",
     "price": "5,990円",  "sale_price": "4,490〜4,990円", "off": "25%", "effective": "約4,150円〜",
     "image_url": _IMG.format("818Yri9ThvL._AC_SL500_.jpg")},
    {"key": "echo_dot",      "asin": "B09B8SZLLG", "name": "Echo Dot 第5世代",
     "price": "7,480円",  "sale_price": "2,980円", "off": "60%", "effective": "約2,756円",
     "image_url": _IMG.format("61bjWOqjJRL._AC_SL500_.jpg")},
    {"key": "fire_tv",       "asin": "B0BW37QY2V", "name": "Fire TV Stick 4K Max",
     "price": "12,980円", "sale_price": "7,980円", "off": "39%", "effective": "約7,382円",
     "image_url": _IMG.format("61z-Y8uUXcL._AC_SL500_.jpg")},
    {"key": "kindle",        "asin": "B0CFPL6CFY", "name": "Kindle Paperwhite 第12世代",
     "price": "27,980円", "sale_price": "19,980円", "off": "29%", "effective": "約18,482円",
     "image_url": _IMG.format("81avQx826IL._AC_SL500_.jpg")},
    {"key": "anker_prime",   "asin": "B0C5CBV6L3", "name": "Anker Prime 67W充電器",
     "price": "5,490円",  "sale_price": "3,990円", "off": "27%", "effective": "約3,691円",
     "image_url": _IMG.format("511Xc9MrA%2BL._AC_SL500_.jpg")},
    {"key": "switchbot",     "asin": "B0BM8VS13P", "name": "SwitchBot ハブ2",
     "price": "9,980円",  "sale_price": "6,980円", "off": "30%", "effective": "約6,458円",
     "image_url": _IMG.format("61c5XcNzYrL._AC_SL500_.jpg")},
    {"key": "ipad_air",      "asin": "B0GQWJCR4K", "name": "iPad Air M4 11インチ",
     "price": "98,800円", "sale_price": "88,000円", "off": "11%", "effective": "約83,000円",
     "image_url": _IMG.format("71cEd-F5hgL._AC_SL500_.jpg")},
    {"key": "jbl_charge5",   "asin": "B0928Y5TPD", "name": "JBL Charge 5",
     "price": "16,980円", "sale_price": "12,800円", "off": "25%", "effective": "約11,840円",
     "image_url": _IMG.format("71wvIo47HzL._AC_SL500_.jpg")},
    {"key": "deco_x50",      "asin": "B0BSTMHPJ2", "name": "TP-Link Deco X50 3台セット",
     "price": "26,320円", "sale_price": "21,000円", "off": "20%", "effective": "約19,425円",
     "image_url": _IMG.format("21reiQyNgeL._AC_SL500_.jpg")},
]

# ===== ユーティリティ =====

def load_templates() -> dict:
    with open(TEMPLATES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_history() -> dict:
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"posted": [], "product_index": 0}


def save_history(history: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def amazon_url(asin: str) -> str:
    return f"https://www.amazon.co.jp/dp/{asin}?tag=teckjpkokuto-22"


def fill(template: str, product: dict = None, category: str = "general") -> str:
    today = date.today()
    days_left = max(0, (SALE_END - today).days)
    kv = {
        "{url}":       BLOG_URL,
        "{sale_end}":  SALE_END.strftime("%m月%d日"),
        "{days_left}": str(days_left),
    }
    if product:
        kv.update({
            "{name}":       product["name"],
            "{price}":      product["price"],
            "{sale_price}": product["sale_price"],
            "{off}":        product["off"],
            "{effective}":  product["effective"],
            "{url}":        amazon_url(product["asin"]),
        })
    result = template
    for k, v in kv.items():
        result = result.replace(k, v)
    result = result.strip()
    tags = _build_hashtags(category, product)
    candidate = result + "\n\n" + tags
    return candidate if len(candidate) <= 500 else result


def pick(pool: list, history: dict, key: str):
    """未使用のテンプレートをランダムに選ぶ。全消費したらリセット。"""
    prefix = f"{key}:"
    used = {int(h[len(prefix):]) for h in history["posted"] if h.startswith(prefix)}
    available = [i for i in range(len(pool)) if i not in used]
    if not available:
        # リセット
        history["posted"] = [h for h in history["posted"] if not h.startswith(prefix)]
        available = list(range(len(pool)))
    idx = random.choice(available)
    history["posted"].append(f"{prefix}{idx}")
    return pool[idx]


def next_product(history: dict) -> dict:
    idx = history.get("product_index", 0) % len(PRODUCTS)
    history["product_index"] = idx + 1
    return PRODUCTS[idx]


# ===== テンプレート選択 =====

def select_post(templates: dict, history: dict) -> tuple:
    """(text, image_url_or_None) を返す"""
    today = date.today()
    is_sale  = SALE_START <= today <= SALE_END
    pre_sale = (SALE_START - today) <= timedelta(days=3) and today < SALE_START

    if is_sale:
        roll = random.random()
        if roll < 0.45:
            p = next_product(history)
            pool = templates.get("sale_product", {}).get(p["key"])
            if pool:
                t = pick(pool, history, f"prod_{p['key']}")
                text = fill(t, p, category="sale_product")
                # 1枚目テンプレート（価格情報あり）は画像付き
                img = p.get("image_url") if "{price}" in t else None
                return text, img
            t = pick(templates["general"], history, "general")
            return fill(t, category="general"), None
        elif roll < 0.70:
            t = pick(templates["point_tips"], history, "point_tips")
            return fill(t, category="point_tips"), None
        elif roll < 0.85:
            t = pick(templates["sale_countdown"], history, "countdown")
            return fill(t, category="sale_countdown"), None
        else:
            t = pick(templates["comparison"], history, "comparison")
            return fill(t, category="comparison"), None

    elif pre_sale:
        t = pick(templates["pre_sale"], history, "pre_sale")
        return fill(t, category="pre_sale"), None

    else:
        roll = random.random()
        if roll < 0.65:
            t = pick(templates["general"], history, "general")
            return fill(t, category="general"), None
        elif roll < 0.85:
            t = pick(templates["comparison"], history, "comparison")
            return fill(t, category="comparison"), None
        else:
            t = pick(templates["follow"], history, "follow")
            return fill(t, category="follow"), None


# ===== Threads API =====

def post_to_threads(text: str, image_url: str = None) -> bool:
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not user_id or not token:
        print("[ERROR] THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定", flush=True)
        return False

    base = "https://graph.threads.net/v1.0"

    # コンテナ作成
    if image_url:
        params = {"media_type": "IMAGE", "image_url": image_url, "text": text, "access_token": token}
        print(f"[INFO] 画像付き投稿: {image_url[:60]}...", flush=True)
    else:
        params = {"media_type": "TEXT", "text": text, "access_token": token}

    r1 = requests.post(f"{base}/{user_id}/threads", params=params, timeout=15)
    if r1.status_code != 200:
        print(f"[ERROR] コンテナ作成失敗: {r1.status_code} {r1.text[:200]}", flush=True)
        if image_url:
            # 画像投稿失敗時はテキストのみで再試行
            print("[INFO] テキスト投稿にフォールバック", flush=True)
            return post_to_threads(text, image_url=None)
        return False

    container_id = r1.json().get("id", "")
    if not container_id:
        print("[ERROR] container_id 取得失敗", flush=True)
        return False

    # 画像の場合はコンテナ処理を待つ（最大30秒）
    if image_url:
        for _ in range(6):
            time.sleep(5)
            rs = requests.get(
                f"{base}/{container_id}",
                params={"fields": "status,error_message", "access_token": token},
                timeout=10,
            )
            status = rs.json().get("status", "")
            if status == "FINISHED":
                break
            if status == "ERROR":
                err = rs.json().get("error_message", "")
                print(f"[WARN] 画像処理エラー: {err} → テキスト投稿にフォールバック", flush=True)
                return post_to_threads(text, image_url=None)
            print(f"[INFO] コンテナ処理中... ({status})", flush=True)
    else:
        time.sleep(3)

    r2 = requests.post(
        f"{base}/{user_id}/threads_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=15,
    )
    if r2.status_code == 200:
        mode = "画像付き" if image_url else "テキスト"
        print(f"[OK] {mode}投稿成功: post_id={r2.json().get('id','')}", flush=True)
        return True
    else:
        print(f"[ERROR] 公開失敗: {r2.status_code} {r2.text[:200]}", flush=True)
        return False


# ===== メイン =====

def main():
    dry_run = "--dry-run" in sys.argv

    templates = load_templates()
    history   = load_history()

    text, image_url = select_post(templates, history)

    # GitHub Actions ログに UTF-8 で出力
    sys.stdout.buffer.write(("=" * 50 + "\n").encode("utf-8"))
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    sys.stdout.buffer.write(("=" * 50 + "\n").encode("utf-8"))
    sys.stdout.buffer.write(f"文字数: {len(text)}\n".encode("utf-8"))
    if image_url:
        sys.stdout.buffer.write(f"画像URL: {image_url}\n".encode("utf-8"))
    sys.stdout.buffer.flush()

    if dry_run:
        print("[DRY-RUN] 投稿スキップ", flush=True)
        save_history(history)
        return

    ok = post_to_threads(text, image_url=image_url)
    if ok:
        save_history(history)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
