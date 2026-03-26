"""
Amazon価格自動取得スクリプト
- 各商品の現在価格をAmazonからスクレイピング
- threads_post.py の PRODUCTS を自動更新
- 実行: python _pipeline/scripts/price_check.py [--dry-run]
"""

import re
import sys
import time
import subprocess
from pathlib import Path

import requests

ROOT         = Path(__file__).parent.parent.parent   # site/
POST_SCRIPT  = ROOT / "_pipeline" / "scripts" / "threads_post.py"
TAG          = "teckjpkokuto-22"

PRODUCTS = [
    {"key": "airpods_pro3",  "asin": "B0FQFQDN6K", "name": "AirPods Pro 3"},
    {"key": "sony_wf_xm6",   "asin": "B0GL7VS33K", "name": "Sony WF-1000XM6"},
    {"key": "sony_wh_xm6",   "asin": "B0F77PMC1P", "name": "Sony WH-1000XM6"},
    {"key": "liberty4nc",    "asin": "B0C1P1N98V", "name": "Soundcore Liberty 4 NC"},
    {"key": "echo_dot",      "asin": "B09B8SZLLG", "name": "Echo Dot 第5世代"},
    {"key": "fire_tv",       "asin": "B0BW37QY2V", "name": "Fire TV Stick 4K Max"},
    {"key": "kindle",        "asin": "B0CFPL6CFY", "name": "Kindle Paperwhite 第12世代"},
    {"key": "anker_prime",   "asin": "B0C5CBV6L3", "name": "Anker Prime 67W充電器"},
    {"key": "switchbot",     "asin": "B0BM8VS13P", "name": "SwitchBot ハブ2"},
    {"key": "ipad_air",      "asin": "B0GQWJCR4K", "name": "iPad Air M4 11インチ"},
    {"key": "jbl_charge5",   "asin": "B0928Y5TPD", "name": "JBL Charge 5"},
    {"key": "deco_x50",      "asin": "B0BSTMHPJ2", "name": "TP-Link Deco X50 3台セット"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_price(asin: str) -> dict | None:
    """Amazonページから価格情報を取得"""
    url = f"https://www.amazon.co.jp/dp/{asin}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text

        # セール価格（赤字の価格）
        sale_match = re.search(
            r'class="[^"]*a-price[^"]*"[^>]*>.*?'
            r'<span[^>]*a-offscreen[^>]*>\s*￥([\d,]+)',
            html, re.DOTALL
        )
        # 通常価格（取り消し線）
        orig_match = re.search(
            r'basisPrice[^>]*>.*?'
            r'<span[^>]*a-offscreen[^>]*>\s*￥([\d,]+)',
            html, re.DOTALL
        )
        # シンプルな価格パターン（バックアップ）
        simple_match = re.search(
            r'"priceAmount":([\d.]+)',
            html
        )
        # corePriceBlockBuyingPrice
        core_match = re.search(
            r'corePriceDisplay_desktop_feature_div.*?'
            r'<span[^>]*a-offscreen[^>]*>\s*￥([\d,]+)',
            html, re.DOTALL
        )

        sale_price = None
        orig_price = None

        if core_match:
            sale_price = core_match.group(1).replace(",", "")
        elif sale_match:
            sale_price = sale_match.group(1).replace(",", "")
        elif simple_match:
            sale_price = str(int(float(simple_match.group(1))))

        if orig_match:
            orig_price = orig_match.group(1).replace(",", "")

        if not sale_price:
            return None

        sale_int  = int(sale_price)
        orig_int  = int(orig_price) if orig_price else sale_int
        off_pct   = int((orig_int - sale_int) / orig_int * 100) if orig_int > sale_int else 0
        effective = int(sale_int * 0.925)

        return {
            "price":      f"{orig_int:,}円",
            "sale_price": f"{sale_int:,}円",
            "off":        f"{off_pct}%",
            "effective":  f"約{effective:,}円",
        }

    except Exception as e:
        print(f"  [ERROR] {asin}: {e}", flush=True)
        return None


def update_threads_post(results: dict):
    """threads_post.py の PRODUCTS を実際の価格で書き換え"""
    src = POST_SCRIPT.read_text(encoding="utf-8")

    for key, data in results.items():
        # {"key": "airpods_pro3", ..., "price": "37,165円", "sale_price": ...} の各フィールドを更新
        for field, value in data.items():
            # "price": "旧値" → "price": "新値"
            pattern = rf'("key":\s*"{re.escape(key)}".*?"' + field + r'":\s*")[^"]+(")'
            replacement = rf'\g<1>{value}\2'
            src = re.sub(pattern, replacement, src, flags=re.DOTALL)

    POST_SCRIPT.write_text(src, encoding="utf-8")


def git_commit_push():
    cmds = [
        ["git", "add", "_pipeline/scripts/threads_post.py"],
        ["git", "commit", "-m", "fix: Amazon新生活セール実際の価格に更新"],
        ["git", "pull", "--rebase"],
        ["git", "push"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[WARN] {' '.join(cmd)}: {r.stderr[:100]}", flush=True)
        else:
            print(f"[OK] {' '.join(cmd)}", flush=True)


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60, flush=True)
    print("Amazon新生活セール 価格自動確認", flush=True)
    print("=" * 60, flush=True)

    results = {}
    for p in PRODUCTS:
        print(f"\n確認中: {p['name']} ...", flush=True)
        data = fetch_price(p["asin"])
        if data:
            results[p["key"]] = data
            print(f"  通常: {data['price']} → セール: {data['sale_price']} ({data['off']}OFF)", flush=True)
            print(f"  実質: {data['effective']}", flush=True)
        else:
            print(f"  [SKIP] 価格取得失敗 → 既存の値を維持", flush=True)
        time.sleep(2)  # Amazon対策

    print(f"\n取得成功: {len(results)}/{len(PRODUCTS)}件", flush=True)

    if not results:
        print("[ERROR] 価格を1件も取得できませんでした", flush=True)
        sys.exit(1)

    if dry_run:
        print("[DRY-RUN] ファイル更新・pushをスキップ", flush=True)
        return

    update_threads_post(results)
    print("[OK] threads_post.py を更新しました", flush=True)

    git_commit_push()


if __name__ == "__main__":
    main()
