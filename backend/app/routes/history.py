import json

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..services.recommender import recommend, with_image_urls
from ..services.report_text import NO_REPORT_TEXT, format_report_text
from ..services.timeutil import kst_date_text

bp = Blueprint("history", __name__)


def _loads(text, default=None):
    try:
        return json.loads(text) if text else default
    except ValueError:
        return default


@bp.get("/history/<user_id>")
def get_history(user_id):
    """분석 기록. 기본은 최신순(앱 화면용), ?order=asc 이면 오래된 순.

    각 항목은 앱의 SkinAnalysisResponse 모양(success, total_score, scores, date,
    llm_report(글), recommendations)과 기존 필드(score_total 등)를 함께 담는다.
    """
    direction = "ASC" if request.args.get("order", "desc").lower() == "asc" else "DESC"
    db = get_db()
    rows = db.execute(
        f"""
        SELECT analyses_id, score_total, score_acne, score_pore,
               score_pigmentation, score_sebum, raw_values, llm_report, recommendations, created_at
        FROM skin_analyses
        WHERE user_id = ?
        ORDER BY created_at {direction}, analyses_id {direction}
        """,
        (user_id,),
    ).fetchall()

    history = []
    for row in rows:
        h = dict(row)
        stored = _loads(h["llm_report"])
        report_data = stored.get("report") if isinstance(stored, dict) else None
        scores = {
            "acne": h["score_acne"], "pigmentation": h["score_pigmentation"],
            "pore": h["score_pore"], "sebum": h["score_sebum"],
        }
        recs = _loads(h["recommendations"])
        if not recs:  # 추천이 저장되지 않은 예전 기록은 점수로 다시 계산한다
            recs = recommend(db, scores)

        h["success"] = True
        h["date"] = kst_date_text(h["created_at"])
        h["total_score"] = h["score_total"]
        h["scores"] = scores
        h["raw_values"] = _loads(h["raw_values"], {})
        h["llm_report"] = format_report_text(report_data) or NO_REPORT_TEXT
        h["llm_report_data"] = report_data
        h["llm_metadata"] = stored.get("metadata") if isinstance(stored, dict) else None
        h["recommendations"] = with_image_urls(recs, request.host_url)
        history.append(h)

    return jsonify({"success": True, "user_id": user_id, "history": history}), 200
