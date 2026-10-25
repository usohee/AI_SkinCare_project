import json
import uuid

from flask import Blueprint, jsonify, request

from llm_service import generate_report  # LLM 담당 모듈 (backend/llm_service.py)

from ..db import get_db
from ..services.skin_analyzer import ImageDecodeError, analyze_image, decode_image

bp = Blueprint("analysis", __name__)


@bp.post("/analyze-skin")
def analyze_skin():
    """사진 1장 → 분석 점수 → LLM 리포트 → DB 저장 → 응답."""
    if "image" not in request.files:
        return jsonify({"success": False, "message": "이미지 없음"}), 400
    try:
        img_bgr = decode_image(request.files["image"].read())
    except ImageDecodeError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    result = analyze_image(img_bgr)
    llm_result = generate_report({
        "success": True,
        "total_score": result["total_score"],
        "scores": result["scores"],
        "raw_values": result["raw_values"],
    })

    user_id = request.form.get("user_id") or str(uuid.uuid4())
    scores = result["scores"]
    db = get_db()
    db.execute(
        """
        INSERT INTO skin_analyses
        (user_id, score_total, score_acne, score_pore, score_pigmentation, score_sebum, raw_values, llm_report)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, result["total_score"],
            scores["acne"], scores["pore"], scores["pigmentation"], scores["sebum"],
            json.dumps(result["raw_values"]),
            json.dumps(llm_result, ensure_ascii=False),
        ),
    )
    db.commit()

    return jsonify({
        "success": True,
        "user_id": user_id,
        "total_score": result["total_score"],
        "scores": scores,
        "raw_values": result["raw_values"],
        "llm_report": llm_result["report"],
        "llm_metadata": llm_result["metadata"],
        "llm_error": llm_result["error"],
    }), 200
