import json
import uuid

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db

bp = Blueprint("auth", __name__)


@bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password")
    nickname = data.get("nickname", "")

    if not email or not password:
        return jsonify({"success": False, "message": "이메일/비밀번호 필요"}), 400
    if "@" not in email:
        return jsonify({"success": False, "message": "이메일 형식이 올바르지 않습니다."}), 400

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify({"success": False, "message": "이미 가입된 이메일입니다."}), 409

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (user_id, email, password_hash, nickname) VALUES (?, ?, ?, ?)",
        (user_id, email, generate_password_hash(password), nickname),
    )
    db.commit()
    return jsonify({"success": True, "user_id": user_id}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not password or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "이메일 또는 비밀번호가 틀렸습니다."}), 401
    return jsonify({"success": True, "user_id": user["user_id"], "nickname": user["nickname"]}), 200


@bp.put("/users/<user_id>/profile")
def update_profile(user_id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone() is None:
        return jsonify({"success": False, "message": "존재하지 않는 사용자"}), 404

    db.execute(
        """
        UPDATE users
        SET gender = ?, birth_year = ?, skin_type = ?,
            skin_concern = ?, allergy_ingredients = ?, preferred_formulations = ?
        WHERE user_id = ?
        """,
        (
            data.get("gender"),
            data.get("birth_year"),
            data.get("skin_type"),
            json.dumps(data.get("skin_concern", []), ensure_ascii=False),
            json.dumps(data.get("allergy_ingredients", []), ensure_ascii=False),
            json.dumps(data.get("preferred_formulations", []), ensure_ascii=False),
            user_id,
        ),
    )
    db.commit()
    return jsonify({"success": True, "user_id": user_id}), 200


@bp.get("/users/<user_id>/profile")
def get_profile(user_id):
    user = get_db().execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if user is None:
        return jsonify({"success": False, "message": "존재하지 않는 사용자"}), 404

    profile = dict(user)
    profile.pop("password_hash", None)  # 비밀번호 해시는 응답에 절대 포함하지 않음
    for field in ("skin_concern", "allergy_ingredients", "preferred_formulations"):
        profile[field] = json.loads(profile[field]) if profile[field] else []
    return jsonify({"success": True, "profile": profile}), 200
