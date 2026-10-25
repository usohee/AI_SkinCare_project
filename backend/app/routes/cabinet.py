from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("cabinet", __name__)

ROUTINE_TIMES = ("MORNING", "NIGHT", "ALL", "NONE")


@bp.post("/users/<user_id>/cabinet")
def add_to_cabinet(user_id):
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    routine_time = data.get("routine_time", "NONE")

    if product_id is None:
        return jsonify({"success": False, "message": "product_id 필요"}), 400
    if routine_time not in ROUTINE_TIMES:
        return jsonify({"success": False, "message": "routine_time은 MORNING/NIGHT/ALL/NONE 중 하나"}), 400

    db = get_db()
    if db.execute("SELECT 1 FROM products WHERE product_id = ?", (product_id,)).fetchone() is None:
        return jsonify({"success": False, "message": "존재하지 않는 제품"}), 404

    cur = db.execute(
        "INSERT INTO user_cabinets (user_id, product_id, is_in_routine, routine_time) VALUES (?, ?, ?, ?)",
        (user_id, product_id, "true", routine_time),
    )
    db.commit()
    return jsonify({"success": True, "cabinet_id": cur.lastrowid}), 201


@bp.get("/users/<user_id>/cabinet")
def get_cabinet(user_id):
    rows = get_db().execute(
        """
        SELECT c.cabinet_id, c.is_in_routine, c.routine_time, c.created_at,
               p.product_id, p.product_name, p.brand, p.ingredients,
               p.category, p.formulation, p.image_url
        FROM user_cabinets c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = ?
        ORDER BY c.created_at DESC, c.cabinet_id DESC
        """,
        (user_id,),
    ).fetchall()
    return jsonify({"success": True, "cabinet": [dict(r) for r in rows]}), 200
