"""LLM 리포트(dict)를 앱 화면에 그대로 보여 줄 수 있는 읽기 쉬운 글로 바꾼다.

앱의 말풍선(Text)은 문자열 하나만 받는다. 리포트 dict를 그대로 문자열로 바꾸면
{'summary': '...', 'indicators': {...}} 처럼 보이므로, 이 함수로 문단을 나누어 만든다.
"""

_ORDER = ("acne", "pigmentation", "pore", "sebum")
EMPTY_REPORT_TEXT = "AI 리포트를 만들지 못했습니다. 잠시 후 다시 시도해 주세요."
NO_REPORT_TEXT = "이 기록에는 저장된 리포트가 없습니다."


def format_report_text(report):
    """report: {summary, indicators, care_tips, caution} → 문단으로 나눈 글. 비어 있으면 None."""
    if not isinstance(report, dict):
        return None
    blocks = []

    summary = str(report.get("summary") or "").strip()
    if summary:
        blocks.append(summary)

    indicators = report.get("indicators") or {}
    lines = [f"• {str(indicators[k]).strip()}" for k in _ORDER if indicators.get(k)]
    if lines:
        blocks.append("■ 항목별 결과\n" + "\n".join(lines))

    tips = [str(t).strip() for t in (report.get("care_tips") or []) if str(t).strip()]
    if tips:
        blocks.append("■ 관리 팁\n" + "\n".join(f"• {t}" for t in tips))

    caution = str(report.get("caution") or "").strip()
    if caution:
        blocks.append(f"※ {caution}")

    return "\n\n".join(blocks) if blocks else None
