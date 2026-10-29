"""Anthropic(Claude) SDK 경계. provider.py(OpenAI)와 같은 인터페이스를 가진다.

예외 본문/키/요청 내용을 로그에 남기지 않고, ProviderError 코드만 위로 올린다.
JSON 형식은 '도구 호출(tool use)'을 강제해서 받는다 → 응답이 항상 스키마에 맞는 dict가 된다.
"""
from .provider import ProviderError

TOOL_NAME = "submit_report"


def request_report(system, user, schema, *, api_key, model):
    try:
        import anthropic
    except ImportError:
        raise ProviderError("SDK_MISSING") from None
    try:
        # 기본 재시도 없음: 한 번의 리포트 요청은 한 번의 API 호출만 한다.
        with anthropic.Anthropic(api_key=api_key, timeout=30.0, max_retries=0) as client:
            response = client.messages.create(
                model=model,
                max_tokens=1800,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[{
                    "name": TOOL_NAME,
                    "description": "검증된 facts와 guidelines만 사용해 작성한 피부 분석 리포트를 제출한다.",
                    "input_schema": schema,
                }],
                tool_choice={"type": "tool", "name": TOOL_NAME},
            )
    except anthropic.APITimeoutError:
        raise ProviderError("TIMEOUT") from None
    except anthropic.APIConnectionError:
        raise ProviderError("NETWORK_ERROR") from None
    except anthropic.APIStatusError as exc:
        status = exc.status_code
        message = str(getattr(exc, "message", "")).lower()
        if status == 400 and "credit balance" in message:
            code = "INSUFFICIENT_CREDIT"
        else:
            code = {401: "AUTHENTICATION_ERROR", 403: "ACCESS_DENIED", 404: "MODEL_NOT_FOUND",
                    429: "RATE_LIMIT", 529: "OVERLOADED"}.get(status, "API_ERROR")
        raise ProviderError(code) from None

    if response.stop_reason == "refusal":
        raise ProviderError("MODEL_REFUSAL")
    if response.stop_reason == "max_tokens":
        raise ProviderError("INCOMPLETE_RESPONSE")
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == TOOL_NAME:
            if isinstance(block.input, dict):
                return block.input
            break
    raise ProviderError("INVALID_JSON")
