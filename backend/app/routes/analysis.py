import json
import uuid

from flask import Blueprint, jsonify, request

from llm_service import generate_report  # LLM 담당 모듈 (backend/llm_service.py)

from ..db import get_db
from ..services.recommender import recommend, with_image_urls
from ..services.report_text import EMPTY_REPORT_TEXT, format_report_text
from ..services.skin_analyzer import ImageDecodeError, analyze_image, decode_image
from ..services.timeutil import today_kst_text

bp = Blueprint("analysis", __name__)


@bp.post("/analyze-skin")
def analyze_skin():
    """사진 1장 → 분석 점수 → LLM 리포트 → 추천 제품 → DB 저장 → 응답.

    응답의 llm_report 는 앱 화면에 바로 보여 줄 수 있는 '글(문자열)'이고,
    같은 내용의 구조화된 데이터는 llm_report_data 에 들어 있다.
    """
    if "image" not in request.files:
        return jsonify({"success": False, "message": "이미지 없음"}), 400
    try:
        img_bgr = decode_image(request.files["image"].read())
    except ImageDecodeError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    result = analyze_image(img_bgr)
    scores = result["scores"]
    llm_result = generate_report({
        "success": True,
        "total_score": result["total_score"],
        "scores": scores,
        "raw_values": result["raw_values"],
    })
    report_data = llm_result["report"]
    report_text = format_report_text(report_data) or EMPTY_REPORT_TEXT

    db = get_db()
    recs = recommend(db, scores)
    user_id = request.form.get("user_id") or str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO skin_analyses
        (user_id, score_total, score_acne, score_pore, score_pigmentation, score_sebum,
         raw_values, llm_report, recommendations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, result["total_score"],
            scores["acne"], scores["pore"], scores["pigmentation"], scores["sebum"],
            json.dumps(result["raw_values"]),
            json.dumps(llm_result, ensure_ascii=False),
            json.dumps(recs, ensure_ascii=False),
        ),
    )
    db.commit()

    return jsonify({
        "success": True,
        "user_id": user_id,
        "date": today_kst_text(),
        "total_score": result["total_score"],
        "scores": scores,
        "raw_values": result["raw_values"],
        "llm_report": report_text,
        "llm_report_data": report_data,
        "llm_metadata": llm_result["metadata"],
        "llm_error": llm_result["error"],
        "recommendations": with_image_urls(recs, request.host_url),
    }), 200
