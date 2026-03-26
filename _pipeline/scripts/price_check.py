"""
セール価格確認スクリプト
3/28 朝に実行して実際のAmazon価格を確認 → threads_post.py の PRODUCTS を更新する

実行: python _pipeline/scripts/price_check.py
"""

from pathlib import Path
import sys

# threads_post.py と同じ商品データを参照
sys.path.insert(0, str(Path(__file__).parent))

PRODUCTS = [
    {"key": "airpods_pro3",  "asin": "B0FQFQDN6K", "name": "AirPods Pro 3",
     "price_est": "37,165円", "sale_est": "32,800円", "off_est": "12%"},
    {"key": "sony_wf_xm6",   "asin": "B0GL7VS33K", "name": "Sony WF-1000XM6",
     "price_est": "45,000円", "sale_est": "38,000円", "off_est": "16%"},
    {"key": "sony_wh_xm6",   "asin": "B0F77PMC1P", "name": "Sony WH-1000XM6",
     "price_est": "59,192円", "sale_est": "52,000円", "off_est": "12%"},
    {"key": "liberty4nc",    "asin": "B0C1P1N98V", "name": "Soundcore Liberty 4 NC",
     "price_est": "5,990円",  "sale_est": "4,490円",  "off_est": "25%"},
    {"key": "echo_dot",      "asin": "B09B8SZLLG", "name": "Echo Dot 第5世代",
     "price_est": "7,480円",  "sale_est": "2,980円",  "off_est": "60%"},
    {"key": "fire_tv",       "asin": "B0BW37QY2V", "name": "Fire TV Stick 4K Max",
     "price_est": "12,980円", "sale_est": "7,980円",  "off_est": "39%"},
    {"key": "kindle",        "asin": "B0CFPL6CFY", "name": "Kindle Paperwhite 第12世代",
     "price_est": "27,980円", "sale_est": "19,980円", "off_est": "29%"},
    {"key": "anker_prime",   "asin": "B0C5CBV6L3", "name": "Anker Prime 67W充電器",
     "price_est": "5,490円",  "sale_est": "3,990円",  "off_est": "27%"},
    {"key": "switchbot",     "asin": "B0BM8VS13P", "name": "SwitchBot ハブ2",
     "price_est": "9,980円",  "sale_est": "6,980円",  "off_est": "30%"},
    {"key": "ipad_air",      "asin": "B0GQWJCR4K", "name": "iPad Air M4 11インチ",
     "price_est": "98,800円", "sale_est": "88,000円", "off_est": "11%"},
    {"key": "jbl_charge5",   "asin": "B0928Y5TPD", "name": "JBL Charge 5",
     "price_est": "16,980円", "sale_est": "12,800円", "off_est": "25%"},
    {"key": "deco_x50",      "asin": "B0BSTMHPJ2", "name": "TP-Link Deco X50 3台セット",
     "price_est": "26,320円", "sale_est": "21,000円", "off_est": "20%"},
]

TAG = "teckjpkokuto-22"

print("=" * 60)
print("Amazon新生活セール 価格確認チェックリスト")
print("各リンクを開いて実際の価格を確認し、threads_post.py を更新してください")
print("=" * 60)
print()

for p in PRODUCTS:
    url = f"https://www.amazon.co.jp/dp/{p['asin']}?tag={TAG}"
    print(f"【{p['name']}】")
    print(f"  予想: 通常 {p['price_est']} → セール {p['sale_est']}（{p['off_est']}OFF）")
    print(f"  確認: {url}")
    print(f"  実際: 通常 ______円 → セール ______円（ ______ %OFF）")
    print()

print("=" * 60)
print("更新箇所: site/_pipeline/scripts/threads_post.py の PRODUCTS リスト")
print("  price      → 実際の通常価格")
print("  sale_price → 実際のセール価格")
print("  off        → 割引率（小数点以下切り捨て）")
print("  effective  → ポイント還元後の実質価格（sale_price × 0.925 の目安）")
print("=" * 60)
