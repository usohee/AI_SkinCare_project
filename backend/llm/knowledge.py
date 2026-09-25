"""확인된 자료만 항목별로 선택한다. 네트워크 접근 없이 동작한다."""
import json
from pathlib import Path

KB_PATH = Path(__file__).with_name("knowledge_base.json")


def select_guidelines(scores):
    kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
    # 가장 큰 감점 두 항목의 자료 + 공통 보습/자외선/상담 자료만 전달한다.
    ranked = sorted(scores, key=lambda key: -scores[key])
    focus = {key for key in ranked[:2] if scores[key] > 0}
    selected = [entry for entry in kb["entries"] if entry["verified"] and
                (entry["general"] or focus.intersection(entry["indicators"]))]
    return kb["version"], selected


def public_sources(entries):
    fields = ("id", "title", "publisher", "url", "published_or_updated", "checked_at", "evidence", "guidance")
    return [{key: entry[key] for key in fields} for entry in entries]
