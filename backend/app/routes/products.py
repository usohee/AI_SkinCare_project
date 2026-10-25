from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("products", __name__)


@bp.post("/products/bulk-import")
def bulk_import_products():
    """제품/성분 데이터를 한 번에 넣는 용도. 같은 이름+브랜드는 건너뛴다."""
    data = request.get_json(silent=True) or {}
    products = data.get("products", [])
    db = get_db()
    inserted = skipped = 0
    for p in products:
        name = p.get("product_name")
        if not name:
            skipped += 1
            continue
        exists = db.execute(
            "SELECT 1 FROM products WHERE product_name = ? AND IFNULL(brand, '') = IFNULL(?, '')",
            (name, p.get("brand")),
        ).fetchone()
        if exists:
            skipped += 1
            continue
        db.execute(
            """
            INSERT INTO products (product_name, brand, ingredients, category, formulation, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, p.get("brand"), p.get("ingredients"), p.get("category"),
             p.get("formulation"), p.get("image_url")),
        )
        inserted += 1
    db.commit()
    return jsonify({"success": True, "inserted": inserted, "skipped": skipped}), 201


@bp.get("/products")
def list_products():
    """제품 검색 (?q=검색어)"""
    keyword = request.args.get("q", "")
    rows = get_db().execute(
        "SELECT * FROM products WHERE product_name LIKE ? ORDER BY product_id DESC",
        (f"%{keyword}%",),
    ).fetchall()
    return jsonify({"success": True, "products": [dict(r) for r in rows]}), 200
