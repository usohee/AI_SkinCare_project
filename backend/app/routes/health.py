import os

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    """서버 상태 확인. 시연 전에 브라우저로 열어 보면 된다. (키 값은 노출하지 않는다)"""
    return jsonify({
        "status": "ok",
        "llm_configured": bool(os.getenv("OPENAI_API_KEY", "").strip() and os.getenv("OPENAI_MODEL", "").strip()),
    })
