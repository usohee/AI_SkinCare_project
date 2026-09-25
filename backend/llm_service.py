"""공개 인터페이스: generate_report(analysis_data, mode='auto'). 기존 서버를 import하지 않는다."""
import argparse
import json
import os
from pathlib import Path
import sys

if __package__:
    from .llm.contracts import InputError, OutputError, validate_input, interpret
    from .llm.knowledge import select_guidelines, public_sources
    from .llm.prompts import build_prompts, output_schema, PROMPT_VERSION
    from .llm.provider import request_report, ProviderError
    from .llm.output import validate_output, fallback_report
else:
    from llm.contracts import InputError, OutputError, validate_input, interpret
    from llm.knowledge import select_guidelines, public_sources
    from llm.prompts import build_prompts, output_schema, PROMPT_VERSION
    from llm.provider import request_report, ProviderError
    from llm.output import validate_output, fallback_report


def generate_report(analysis_data, *, mode="auto"):
    """auto: LLM 실패 시 fallback, offline: 호출 없음, llm: 실패를 숨기지 않음.

    항상 {success, report, metadata, error}를 반환한다.
    입력 오류는 report=None이며 가짜 피부 리포트를 만들지 않는다.
    """
    meta = {"source": "none", "llm_success": False, "llm_attempted": False, "model": None,
            "prompt_version": PROMPT_VERSION, "knowledge_version": None, "warnings": [],
            "fallback_reason": None, "sources": [], "priority_indicators": []}
    result = {"success": False, "report": None, "metadata": meta, "error": None}
    if mode not in ("auto", "offline", "llm"):
        result["error"] = {"code": "INVALID_MODE", "message": "mode는 auto, offline, llm 중 하나여야 합니다."}
        return result
    try:
        data, meta["warnings"] = validate_input(analysis_data)
    except InputError as exc:
        result["error"] = {"code": "INVALID_INPUT", "message": str(exc)}
        return result
    facts = interpret(data)
    meta["priority_indicators"] = facts["priority_indicators"]
    try:
        version, guidelines = select_guidelines(data["scores"])
        if not guidelines:
            raise ValueError("empty knowledge base")
        meta["knowledge_version"] = version
    except (OSError, ValueError, KeyError, TypeError):
        result["error"] = {"code": "KNOWLEDGE_ERROR", "message": "지식 베이스 파일을 확인하세요."}
        return result
    reason = "OFFLINE_MODE"
    if mode != "offline":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        if not key:
            reason = "MISSING_API_KEY"
        elif not model:
            reason = "MISSING_MODEL"
        else:
            meta["model"] = model
            meta["llm_attempted"] = True
            system, user = build_prompts(data, facts, guidelines)
            try:
                candidate = request_report(system, user, output_schema(guidelines), api_key=key, model=model)
                report, ids = validate_output(candidate, facts, guidelines)
                result.update(success=True, report=report)
                meta.update(source="llm", llm_success=True, sources=public_sources([e for e in guidelines if e["id"] in ids]))
                return result
            except ProviderError as exc:
                reason = exc.code
            except OutputError:
                reason = "INVALID_OUTPUT"
            except Exception:
                # SDK 변경 등 예상 밖 외부 오류도 서버를 중단시키거나 비밀값을 노출하지 않는다.
                reason = "UNEXPECTED_PROVIDER_ERROR"
    if mode == "llm":
        result["error"] = {"code": reason, "message": "실제 LLM 리포트를 생성하지 못했습니다. 환경설정과 API 연결을 확인하세요."}
        return result
    result.update(success=True, report=fallback_report(facts, guidelines))
    meta.update(source="fallback", fallback_reason=reason, sources=public_sources(guidelines))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mirror Me 피부 수치 리포트 생성")
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "examples" / "analysis.json")
    parser.add_argument("--mode", choices=("offline", "auto", "llm"), default="offline",
                        help="기본 offline. llm은 실제 호출 실패 시 종료 코드 1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = generate_report(args.input.read_text(encoding="utf-8-sig"), mode=args.mode)
    except (OSError, UnicodeError):
        print("입력 파일을 읽지 못했습니다.", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        try:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError:
            print("출력 파일을 저장하지 못했습니다.", file=sys.stderr)
            return 2
    print(rendered)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
