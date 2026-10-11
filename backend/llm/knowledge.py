"""확인된 자료만 항목별로 선택한다. 네트워크 접근 없이 동작한다."""
import json
from pathlib import Path

KB_PATH = Path(__file__).with_name("knowledge_base.json")


def select_guidelines(scores, self_reported_skin_type=None):
    kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
    # 가장 큰 감점 두 항목의 자료 + 공통 보습/자외선/상담 자료만 전달한다.
    ranked = sorted(scores, key=lambda key: -scores[key])
    focus = [key for key in ranked[:2] if scores[key] > 0]
    verified = [e for e in kb["entries"] if e["verified"]]
    selected = [e for e in verified if e["general"] and not e.get("skin_types")]
    for key in focus:
        matches = [e for e in verified if not e["general"] and not e.get("skin_types") and key in e["indicators"]]
        for entry in matches[:2]:
            if entry not in selected:
                selected.append(entry)
    # 점수/밝기로 타입을 추정하지 않는다. 명시된 자기보고 유형과 맞는 자료만 추가한다.
    selected.extend([e for e in verified if self_reported_skin_type in e.get("skin_types", [])][:1])
    return kb["version"], selected


def public_sources(entries):
    fields = ("id", "title", "publisher", "url", "published_or_updated", "checked_at", "evidence", "guidance")
    return [{**{key: entry[key] for key in fields},
             "applicability": entry.get("applicability", "일반 관리 참고 정보"),
             "limitations": entry.get("limitations", "의학적 진단이나 치료 지시가 아님")}
            for entry in entries]
