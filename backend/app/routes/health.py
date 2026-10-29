import os

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


def _llm_status():
    """어떤 LLM 제공자가 설정되어 있는지만 알려 준다. (키 값은 절대 노출하지 않는다)"""
    name = os.getenv("LLM_PROVIDER", "").strip().lower()
    if name not in ("anthropic", "openai"):
        name = "anthropic" if os.getenv("ANTHROPIC_API_KEY", "").strip() else "openai"
    prefix = "ANTHROPIC" if name == "anthropic" else "OPENAI"
    configured = bool(os.getenv(f"{prefix}_API_KEY", "").strip() and os.getenv(f"{prefix}_MODEL", "").strip())
    return name, configured


@bp.get("/health")
def health():
    """서버 상태 확인. 시연 전에 브라우저로 열어 보면 된다."""
    provider, configured = _llm_status()
    return jsonify({"status": "ok", "llm_provider": provider, "llm_configured": configured})
