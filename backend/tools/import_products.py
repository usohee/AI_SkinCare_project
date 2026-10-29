"""제품 데이터(엑셀)를 DB의 products 테이블에 넣는다. 여러 번 실행해도 중복으로 들어가지 않는다.

사용 (backend 폴더에서, 가상환경을 켠 상태):
    python tools/import_products.py
    python tools/import_products.py --xlsx "경로\\skincare_ product_data.xlsx" --db skincare.db
"""
import argparse
import glob
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

from app.config import Config  # noqa: E402
from app.db import init_db  # noqa: E402


def find_xlsx():
    pattern = os.path.join(os.path.dirname(BACKEND), "dataset", "skincare_products_data", "*product_data.xlsx")
    found = sorted(glob.glob(pattern))
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=find_xlsx())
    ap.add_argument("--db", default=Config.DB_PATH)
    args = ap.parse_args()
    if not args.xlsx or not os.path.exists(args.xlsx):
        sys.exit("엑셀 파일을 찾지 못했습니다. --xlsx 로 경로를 지정하세요.")
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl 이 필요합니다:  pip install openpyxl")

    sheet = openpyxl.load_workbook(args.xlsx, data_only=True)["Products"]
    rows = list(sheet.iter_rows(values_only=True))
    header = [str(h).strip() for h in rows[0]]
    idx = {name: header.index(name) for name in ("brand", "product_name", "product_type", "ingredients_raw")}

    init_db(args.db)
    conn = sqlite3.connect(args.db)
    inserted = skipped = 0
    try:
        for r in rows[1:]:
            name = r[idx["product_name"]]
            if not name:
                continue
            brand = r[idx["brand"]]
            dup = conn.execute(
                "SELECT 1 FROM products WHERE product_name = ? AND IFNULL(brand, '') = IFNULL(?, '')",
                (name, brand),
            ).fetchone()
            if dup:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO products (product_name, brand, ingredients, category) VALUES (?, ?, ?, ?)",
                (name, brand, r[idx["ingredients_raw"]], r[idx["product_type"]]),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[완료] 새로 넣은 제품 {inserted}개, 이미 있어서 건너뜀 {skipped}개  →  {args.db}")


if __name__ == "__main__":
    main()
