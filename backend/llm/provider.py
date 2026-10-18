"""공식 OpenAI SDK 경계. 예외 본문/키/요청 내용을 로그에 남기지 않는다."""
import json


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def request_report(system, user, schema, *, api_key, model):
    try:
        from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError
    except ImportError:
        raise ProviderError("SDK_MISSING") from None
    try:
        # 기본 재시도 없음: 한 번의 리포트 요청은 한 번의 API 호출만 한다.
        with OpenAI(api_key=api_key, timeout=30.0, max_retries=0) as client:
            response = client.responses.create(
                model=model, store=False, max_output_tokens=1800,
                input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                text={"format": {"type": "json_schema", "name": "mirror_me_report", "strict": True, "schema": schema}},
            )
        if response.status != "completed":
            raise ProviderError("INCOMPLETE_RESPONSE")
        if any(getattr(part, "type", None) == "refusal" for item in response.output
               for part in getattr(item, "content", [])):
            raise ProviderError("MODEL_REFUSAL")
        try:
            return json.loads(response.output_text)
        except (ValueError, TypeError):
            raise ProviderError("INVALID_JSON") from None
    except APITimeoutError:
        raise ProviderError("TIMEOUT") from None
    except APIConnectionError:
        raise ProviderError("NETWORK_ERROR") from None
    except APIStatusError as exc:
        code = {401: "AUTHENTICATION_ERROR", 403: "ACCESS_DENIED", 429: "RATE_LIMIT"}.get(exc.status_code, "API_ERROR")
        raise ProviderError(code) from None
