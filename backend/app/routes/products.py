import os

from flask import Blueprint, Response, jsonify, request, send_file

from ..db import get_db
from ..services.product_image import kind_for, render_png

bp = Blueprint("products", __name__)

_STATIC_PRODUCTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "products")
_png_cache = {}


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


def product_image_url(product_id):
    return request.host_url.rstrip("/") + f"/product-image/p{product_id}"


@bp.get("/products")
def list_products():
    """제품 검색 (?q=검색어). image_url이 비어 있으면 서버가 만든 제품 이미지 주소를 채운다."""
    keyword = request.args.get("q", "")
    rows = get_db().execute(
        "SELECT * FROM products WHERE product_name LIKE ? ORDER BY product_id DESC",
        (f"%{keyword}%",),
    ).fetchall()
    products = []
    for r in rows:
        item = dict(r)
        item["image_url"] = item["image_url"] or product_image_url(item["product_id"])
        products.append(item)
    return jsonify({"success": True, "products": products}), 200


@bp.get("/product-image/<slug>")
def product_image(slug):
    """제품 이미지. slug: p<제품번호> 또는 t-<종류>.
    backend/app/static/products/<제품번호>.jpg|png|webp 가 있으면 그 사진을, 없으면 종류별 일러스트를 돌려준다."""
    kind = "default"
    if slug.startswith("p") and slug[1:].isdigit():
        pid = int(slug[1:])
        for ext in ("jpg", "jpeg", "png", "webp"):
            path = os.path.join(_STATIC_PRODUCTS, f"{pid}.{ext}")
            if os.path.exists(path):
                return send_file(path, max_age=3600)
        row = get_db().execute("SELECT category FROM products WHERE product_id = ?", (pid,)).fetchone()
        if row is None:
            return jsonify({"success": False, "message": "존재하지 않는 제품"}), 404
        kind = kind_for(row["category"])
    elif slug.startswith("t-"):
        kind = slug[2:]
    else:
        return jsonify({"success": False, "message": "잘못된 이미지 주소"}), 404

    if kind not in _png_cache:
        _png_cache[kind] = render_png(kind)
    resp = Response(_png_cache[kind], mimetype="image/png")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp
