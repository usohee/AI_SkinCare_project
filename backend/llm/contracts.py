"""외부 입력을 검증하고 개인정보를 제외한 분석 수치만 추출한다."""
import json
import math

LABELS = {"acne": "여드름", "pigmentation": "색소침착", "pore": "모공", "sebum": "피지 반사"}
RAW_KEYS = {"acne_count", "pigmentation_count", "pore_variance", "sebum_ratio"}
CAUTION = "본 결과는 이미지 기반 참고 정보이며 의학적 진단을 대체하지 않습니다. 촬영 환경과 알고리즘의 한계에 따라 결과가 달라질 수 있습니다."


class InputError(ValueError):
    pass


class OutputError(ValueError):
    pass


def validate_input(data):
    """dict 또는 JSON 문자열. 점수는 기존 서버와 같은 정수만 허용한다."""
    if isinstance(data, str):
        if len(data) > 65536:
            raise InputError("입력 JSON이 너무 큽니다.")
        try:
            data = json.loads(data)
        except (ValueError, RecursionError):
            raise InputError("올바른 JSON 문자열이 필요합니다.") from None
    if not isinstance(data, dict):
        raise InputError("입력은 JSON 객체여야 합니다.")
    if "success" in data and data["success"] is not True:
        raise InputError("분석에 성공한 데이터만 사용할 수 있습니다.")
    scores = data.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(LABELS):
        raise InputError("scores에는 acne, pigmentation, pore, sebum 네 항목이 필요합니다.")
    for value in [data.get("total_score"), *scores.values()]:
        if type(value) is not int or not 0 <= value <= 100:
            raise InputError("total_score와 개별 점수는 0~100 사이의 정수여야 합니다.")
    raw = data.get("raw_values", {})
    if not isinstance(raw, dict):
        raise InputError("raw_values는 생략하거나 JSON 객체로 전달하세요.")
    clean_raw = {}
    for key in RAW_KEYS & raw.keys():
        value = raw[key]
        if type(value) not in (int, float) or value < 0 or value > 1e12 or not math.isfinite(value):
            raise InputError("raw_values의 알려진 측정값은 유한한 음이 아닌 수여야 합니다.")
        if key.endswith("_count") and (type(value) is not int):
            raise InputError("탐지 개수는 정수여야 합니다.")
        if key == "sebum_ratio" and value > 100:
            raise InputError("sebum_ratio는 서버 응답 기준 0~100 백분율입니다.")
        clean_raw[key] = value
    # 알고리즘의 skin_type은 무시한다. 별도의 사용자 자기보고만 허용한다.
    clean = {"total_score": data["total_score"], "scores": {k: scores[k] for k in LABELS}, "raw_values": clean_raw}
    reported = data.get("self_reported_skin_type")
    if reported is not None:
        if type(reported) is not str or reported not in ("dry", "oily", "combination_oily", "unknown"):
            raise InputError("self_reported_skin_type은 dry, oily, combination_oily, unknown 중 하나여야 합니다.")
        if reported != "unknown":
            clean["self_reported_skin_type"] = reported
    expected = max(0, 100 - round(sum(scores.values()) / 4))
    warnings = []
    if expected != data["total_score"]:
        warnings.append("TOTAL_SCORE_MISMATCH: 전달된 종합 점수가 현재 서버 계산식과 다릅니다. 입력값을 유지했습니다.")
    return clean, warnings


def interpret(data):
    scores = data["scores"]
    highest = max(scores.values())
    priority = [k for k in LABELS if scores[k] == highest] if highest else []
    if highest == 0:
        relative = "모든 항목의 감점이 같습니다. 이 결과만으로 피부 문제가 없다고 단정할 수 없습니다."
    elif len(priority) == 4:
        relative = "모든 항목의 감점이 같아 특정 항목을 우선으로 구분하지 않았습니다."
    else:
        names = ", ".join(LABELS[k] for k in priority)
        relative = f"이번 분석에서는 {names} 항목의 감점이 상대적으로 큽니다. 이는 질환의 중증도나 실제 문제 크기 순위가 아닙니다."
    return {
        "summary": f"종합 점수는 {data['total_score']}점입니다. 종합 점수는 높을수록 양호한 방향입니다. {relative}",
        "indicators": {k: f"{name} 관련 감점은 {scores[k]}점입니다. 개별 점수는 높을수록 감점이 큽니다." for k, name in LABELS.items()},
        "priority_indicators": priority,
    }
