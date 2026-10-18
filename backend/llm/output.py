"""출력 구조·점수 문장·선택된 근거를 검증한다. 의미 검증의 한계는 문서 참조."""
import re
from .contracts import LABELS, CAUTION, OutputError

# 알려진 오해를 방지하는 보수적 필터. 임의의 모든 의료 주장을 판별하는 분류기는 아니다.
FORBIDDEN = ("홍조", "redness", "주름", "피부 나이", "피부나이", "지성", "건성", "복합성", "민감성",
             "수분 부족", "수분부족", "탈수", "장벽 손상", "중증", "경증", "정상 피부", "완치", "치료",
             "처방", "항생제", "레티놀", "호르몬", "세균", "염증", "아토피", "흑색종", "피부염",
             "개선되", "악화되", "지난", "이전보다", "원인은", "때문에 발생", "확진", "진단됩니다")


def validate_output(candidate, facts, guidelines):
    if not isinstance(candidate, dict) or set(candidate) != {"summary", "indicators", "care_tip_ids"}:
        raise OutputError("리포트 필드 불일치")
    indicators = candidate["indicators"]
    if not isinstance(indicators, dict) or set(indicators) != set(LABELS):
        raise OutputError("분석 항목 불일치")
    pairs = [(candidate["summary"], facts["summary"])] + [(indicators[k], facts["indicators"][k]) for k in LABELS]
    for text, fact in pairs:
        if not isinstance(text, str) or len(text) > 700 or not text.startswith(fact):
            raise OutputError("점수/방향/우선순위 사실 문장 불일치")
        suffix = text[len(fact):]
        if suffix and not re.search("[가-힣]", suffix):
            raise OutputError("한국어 설명 필요")
        if re.search(r"\d|https?://|<|>", suffix) or any(word in suffix.lower() for word in FORBIDDEN):
            raise OutputError("근거 없는 수치/분석/주장")
        # 다른 방향을 뒤에 덧붙여 사실 문장을 무효화하지 못하게 한다.
        if any(word in suffix for word in ("높을수록", "낮을수록", "심각", "위험", "양호", "좋은", "나쁜")):
            raise OutputError("추가적인 점수 판정 불가")
    ids = candidate["care_tip_ids"]
    allowed = {entry["id"]: entry for entry in guidelines}
    if not isinstance(ids, list) or not 1 <= len(ids) <= len(allowed) or any(type(i) is not str for i in ids):
        raise OutputError("관리 가이드 ID 형식 오류")
    if len(set(ids)) != len(ids) or any(i not in allowed for i in ids):
        raise OutputError("확인되지 않은 관리 가이드")
    return {"summary": candidate["summary"], "indicators": indicators,
            "care_tips": [allowed[i]["guidance"] for i in ids], "caution": CAUTION}, ids


def fallback_report(facts, guidelines):
    return {"summary": facts["summary"], "indicators": facts["indicators"].copy(),
            "care_tips": [entry["guidance"] for entry in guidelines], "caution": CAUTION}
