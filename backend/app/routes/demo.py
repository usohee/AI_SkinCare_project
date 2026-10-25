"""시연 전용 화면과 도구. 기능 API(/analyze-skin 등)와 분리되어 있어 이 파일만 빼도 서버는 동작한다.

    GET  /demo             대시보드형 시연 화면 (샘플 사진 분석 → 결과 → 기록)
    GET  /app              앱 UI 재현 화면 (backend/demo/mirrorme_demo.html)
    GET  /demo/sample.jpg  시연용 샘플 사진 (backend/test_selfie.jpg)
    POST /demo/seed        시연 계정의 기록을 지우고 과거 샘플 기록 4건을 넣는다 (리허설 초기화)
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, send_file
from werkzeug.security import generate_password_hash

from ..config import BASE_DIR
from ..db import get_db

bp = Blueprint("demo", __name__)

DEMO_USER_ID = "demo-user"
DEMO_EMAIL = "demo@mirrorme.com"
DEMO_PASSWORD = "demo1234"
SAMPLE_FILE = "test_selfie.jpg"
SEED_MARK = "demo-seed"  # image_url 컬럼에 표시해 두어 샘플 기록임을 구분한다

# 과거 샘플 기록: (며칠 전, 여드름, 모공, 색소침착, 피지) — 항목 점수는 감점 기준(낮을수록 양호)
SEED_ROWS = [
    (28, 14, 92, 20, 60),
    (21, 11, 90, 16, 55),
    (14, 9, 88, 12, 50),
    (7, 7, 87, 10, 48),
]

_STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


def ensure_demo_user(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, email, password_hash, nickname) VALUES (?, ?, ?, ?)",
            (DEMO_USER_ID, DEMO_EMAIL, generate_password_hash(DEMO_PASSWORD), "시연 계정"),
        )
        conn.commit()
    finally:
        conn.close()


def _first_existing(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


@bp.get("/demo")
def demo_dashboard():
    ensure_demo_user(current_app.config["DB_PATH"])
    return send_file(os.path.join(_STATIC, "demo_dashboard.html"), mimetype="text/html")


@bp.get("/app")
def demo_app():
    path = _first_existing(
        os.path.join(BASE_DIR, "demo", "mirrorme_demo.html"),
        os.path.join(BASE_DIR, "mirrorme_demo.html"),
    )
    if path is None:
        return "backend/demo/mirrorme_demo.html 파일이 없습니다.", 404
    return send_file(path, mimetype="text/html")


@bp.get("/demo/sample.jpg")
def demo_sample():
    path = _first_existing(
        os.path.join(BASE_DIR, "demo", SAMPLE_FILE),
        os.path.join(BASE_DIR, SAMPLE_FILE),
    )
    if path is None:
        return jsonify({"success": False, "message": f"샘플 사진이 없습니다: backend/{SAMPLE_FILE}"}), 404
    return send_file(path, mimetype="image/jpeg")


@bp.post("/demo/seed")
def demo_seed():
    ensure_demo_user(current_app.config["DB_PATH"])
    now = datetime.now(timezone.utc)
    db = get_db()
    db.execute("DELETE FROM skin_analyses WHERE user_id = ?", (DEMO_USER_ID,))
    for days_ago, acne, pore, pigmentation, sebum in SEED_ROWS:
        total = max(0, 100 - round((acne + pore + pigmentation + sebum) / 4))
        created = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            """
            INSERT INTO skin_analyses
            (user_id, image_url, score_total, score_acne, score_pore,
             score_pigmentation, score_sebum, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (DEMO_USER_ID, SEED_MARK, total, acne, pore, pigmentation, sebum, created),
        )
    db.commit()
    return jsonify({"success": True, "user_id": DEMO_USER_ID, "seeded": len(SEED_ROWS)}), 200
