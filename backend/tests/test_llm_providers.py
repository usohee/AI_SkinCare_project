"""Claude 연동 테스트. 실제 API는 호출하지 않고 SDK 클라이언트를 가짜로 바꿔서 확인한다."""
from types import SimpleNamespace

import httpx
import pytest

anthropic = pytest.importorskip("anthropic")

from llm.contracts import interpret, validate_input  # noqa: E402
from llm.knowledge import select_guidelines  # noqa: E402
from llm_service import generate_report  # noqa: E402

ANALYSIS = {
    "success": True, "total_score": 56,
    "scores": {"acne": 14, "pore": 91, "pigmentation": 59, "sebum": 10},
    "raw_values": {"acne_count": 7, "pigmentation_count": 147, "pore_variance": 24.6, "sebum_ratio": 6.0},
}


def _valid_candidate():
    data, _ = validate_input(ANALYSIS)
    facts = interpret(data)
    _, guidelines = select_guidelines(data["scores"], None)
    return {"summary": facts["summary"], "indicators": facts["indicators"], "care_tip_ids": [guidelines[0]["id"]]}


class FakeClient:
    """anthropic.Anthropic 대역. behavior(kwargs) → 응답 객체 (또는 예외 발생)"""
    behavior = None
    calls = []

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def messages(self):
        return SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        FakeClient.calls.append(kwargs)
        return FakeClient.behavior(kwargs)


@pytest.fixture()
def fake(monkeypatch):
    FakeClient.calls = []
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")
    return FakeClient


def _tool_response(candidate, stop_reason="tool_use"):
    block = SimpleNamespace(type="tool_use", name="submit_report", input=candidate)
    return SimpleNamespace(content=[block], stop_reason=stop_reason)


def _status_error(cls, status, message="x"):
    request = httpx.Request("POST", "https://example.invalid")
    return cls(message, response=httpx.Response(status, request=request), body=None)


def test_claude_success(fake):
    fake.behavior = lambda kw: _tool_response(_valid_candidate())
    result = generate_report(ANALYSIS)
    meta = result["metadata"]
    assert result["success"] and meta["source"] == "llm"
    assert meta["provider"] == "anthropic" and meta["model"] == "claude-test-model"
    assert result["report"]["care_tips"] and result["report"]["caution"]
    call = fake.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "submit_report"}
    assert call["model"] == "claude-test-model"


@pytest.mark.parametrize("exc, reason", [
    (lambda: _status_error(anthropic.AuthenticationError, 401), "AUTHENTICATION_ERROR"),
    (lambda: _status_error(anthropic.RateLimitError, 429), "RATE_LIMIT"),
    (lambda: _status_error(anthropic.NotFoundError, 404), "MODEL_NOT_FOUND"),
    (lambda: _status_error(anthropic.BadRequestError, 400, "Your credit balance is too low"), "INSUFFICIENT_CREDIT"),
    (lambda: _status_error(anthropic.BadRequestError, 400, "other"), "API_ERROR"),
])
def test_claude_errors_fall_back(fake, exc, reason):
    def boom(kw):
        raise exc()
    fake.behavior = boom
    result = generate_report(ANALYSIS)
    meta = result["metadata"]
    assert result["success"] and meta["source"] == "fallback"
    assert meta["fallback_reason"] == reason and meta["provider"] == "anthropic"


def test_claude_invalid_output_falls_back(fake):
    bad = _valid_candidate()
    bad["summary"] = "점수와 상관없는 문장입니다."
    fake.behavior = lambda kw: _tool_response(bad)
    meta = generate_report(ANALYSIS)["metadata"]
    assert meta["source"] == "fallback" and meta["fallback_reason"] == "INVALID_OUTPUT"


def test_claude_refusal_and_empty(fake):
    fake.behavior = lambda kw: SimpleNamespace(content=[], stop_reason="refusal")
    assert generate_report(ANALYSIS)["metadata"]["fallback_reason"] == "MODEL_REFUSAL"
    fake.behavior = lambda kw: SimpleNamespace(content=[], stop_reason="end_turn")
    assert generate_report(ANALYSIS)["metadata"]["fallback_reason"] == "INVALID_JSON"


def test_provider_selection(monkeypatch):
    # 키가 없으면 어느 쪽이든 규칙 기반
    meta = generate_report(ANALYSIS)["metadata"]
    assert meta["source"] == "fallback" and meta["fallback_reason"] == "MISSING_API_KEY"
    # Claude 키만 있고 모델이 없으면 MISSING_MODEL
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert generate_report(ANALYSIS)["metadata"]["fallback_reason"] == "MISSING_MODEL"
    # LLM_PROVIDER=openai 로 고정하면 OpenAI 쪽 설정을 본다
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    meta = generate_report(ANALYSIS)["metadata"]
    assert meta["provider"] == "openai" and meta["fallback_reason"] == "MISSING_API_KEY"


def test_health_reports_provider(client, monkeypatch):
    assert client.get("/health").get_json() == {"status": "ok", "llm_provider": "openai", "llm_configured": False}
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_MODEL", "m")
    body = client.get("/health").get_json()
    assert body["llm_provider"] == "anthropic" and body["llm_configured"] is True


def test_analyze_endpoint_uses_claude(client, fake, jpeg_bytes):
    import io
    fake.behavior = lambda kw: _tool_response(_valid_candidate_for(kw))
    r = client.post("/analyze-skin", data={"image": (io.BytesIO(jpeg_bytes), "a.jpg"), "user_id": "u9"},
                    content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200 and body["llm_metadata"]["source"] == "llm"
    hist = client.get("/history/u9").get_json()["history"]
    assert hist[0]["llm_metadata"]["provider"] == "anthropic"


def _valid_candidate_for(kwargs):
    """서버가 실제로 보낸 프롬프트의 facts를 그대로 되돌려 주는 대역 응답."""
    import json
    payload = json.loads(kwargs["messages"][0]["content"])
    ids = [g["id"] for g in payload["guidelines"]]
    return {"summary": payload["facts"]["summary"], "indicators": payload["facts"]["indicators"], "care_tip_ids": ids[:1]}
