import json

from flask import Blueprint, jsonify

from ..db import get_db

bp = Blueprint("history", __name__)


def _loads(text, default=None):
    try:
        return json.loads(text) if text else default
    except ValueError:
        return default


@bp.get("/history/<user_id>")
def get_history(user_id):
    rows = get_db().execute(
        """
        SELECT analyses_id, score_total, score_acne, score_pore,
               score_pigmentation, score_sebum, raw_values, llm_report, created_at
        FROM skin_analyses
        WHERE user_id = ?
        ORDER BY created_at ASC, analyses_id ASC
        """,
        (user_id,),
    ).fetchall()

    history = []
    for row in rows:
        h = dict(row)
        h["raw_values"] = _loads(h["raw_values"], {})
        stored = _loads(h["llm_report"])
        h["llm_report"] = stored.get("report") if stored else None      # 리포트 본문
        h["llm_metadata"] = stored.get("metadata") if stored else None  # 출처, fallback 여부 등
        history.append(h)

    return jsonify({"success": True, "user_id": user_id, "history": history}), 200
