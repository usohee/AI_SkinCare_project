# Mirror Me LLM 모듈 연동 가이드

이윤석 담당: 피부 분석 수치를 한국어 참고 리포트로 변환하고, 확인한 공식 관리 자료를 연결하는 독립 모듈.
기존 `backend/test.py`, Android 코드, DB 스키마는 수정하지 않았다.

## 1. 바로 실행하기 — Windows PowerShell

VS Code에서 **터미널 → 새 터미널**을 열고 다음 명령을 실행한다.
폴더 이름이 두 번 반복되는 것이 현재 압축 해제 구조에 맞는 경로다.

```powershell
Set-Location 'C:\Users\xhflz\Downloads\AI_SkinCare_project-main\AI_SkinCare_project-main'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m backend.llm_service --mode offline --input examples/analysis.json --output report.local.json
```

프로젝트 전용 `.venv`와 OpenAI SDK는 이번 개발에서 설치했다. 다른 PC에서는 먼저 다음을 실행한다.
가상환경 활성화 스크립트 없이 실행하므로 PowerShell 실행 정책을 바꿀 필요가 없다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt
```

기대 결과: 콘솔과 `report.local.json`에 `success: true`, `metadata.source: "fallback"`,
`llm_success: false`, `fallback_reason: "OFFLINE_MODE"` 및 한국어 리포트가 나타난다.
이것은 정상적인 **규칙 기반 결과**이고 실제 LLM 생성 결과가 아니다.
로컬 모드 자체는 표준 라이브러리만 사용하므로 SDK가 없어도 `python -m backend.llm_service --mode offline`으로 실행 가능하다.

## 2. 입력 계약

Python dict 또는 JSON 문자열을 전달한다. 예시는 `examples/analysis.json`에 있다.

```json
{
  "success": true,
  "user_id": "synthetic_demo_only",
  "total_score": 72,
  "scores": {"acne": 35, "pigmentation": 20, "pore": 40, "sebum": 17},
  "raw_values": {"acne_count": 5, "pigmentation_count": 50, "pore_variance": 10.8, "sebum_ratio": 10.2}
}
```

이 숫자는 사용자가 제공한 구조 설명용 임시 예시다. 특히 여드름 원시값과 감점은 현재 알고리즘으로
역산했을 때 일치하지 않는다. 모듈은 알고리즘 팀이 제공한 `scores`를 해석하며 원시값으로 감점을 다시 만들지 않는다.

| 항목 | 규칙 |
|---|---|
| `total_score` | 필수, 0~100 정수. 높을수록 양호한 방향 |
| `scores` | 필수. 네 항목 전부 0~100 정수. 높을수록 감점이 큼 |
| `success` | 선택. 있으면 정확히 `true`여야 함 |
| `raw_values` | 선택. 알려진 네 측정값만 추출. 음수/NaN/무한대/과도한 값 거부 |
| `sebum_ratio` | 서버 API 기준 0~100 백분율. 내부 알고리즘의 0~1 비율과 다름 |
| `user_id`, 이미지, 이메일 등 | 리포트 생성에 불필요하므로 제외. LLM에 전달하지 않음 |

숫자 문자열, bool, 소수 점수, 누락된 지표, 임의의 `redness` 지표는 오류다.
0점을 누락값으로 취급하지 않는다. 종합 점수가 `100 - round(sum(scores)/4)`와 다르면
원래 종합 점수를 유지하고 `metadata.warnings`에 불일치를 기록한다. Python의 반올림 방식과 같다.

## 2-1. 선택적인 자기보고 피부 타입 (2026-09-28 추가)

최상위에 `"self_reported_skin_type": "dry"`를 선택적으로 추가할 수 있다.
허용값: `dry`, `oily`, `combination_oily`, `unknown`. 생략/null/unknown이면 유형별 자료를 선택하지 않는다.
기존 입력·호출과 호환된다. 알고리즘의 `skin_type`은 계속 무시하며 자기보고 필드로 복사하지 않는다.
`combination_oily`는 원문의 복합지성이며 일반 복합성 전체를 의미하지 않는다.
이 유형만 선택적으로 LLM에 전달하고 사용자 ID·사진·프로필 자유문은 제외한다.

```powershell
.\.venv\Scripts\python.exe -m backend.llm_service --mode offline --input examples/analysis.dry.json --output report.local.json
```

기대 결과: 조건부 건조피부 관리 안내와 대한피부과학회 원문 출처가 포함된다.
선택량: 상위 감점 두 항목에서 각 최대 2개 + 공통 3개 + 유형 최대 1개. 일반 예시 7개, 유형 예시 8개다.
다른 유형 자료 ID를 모델이 선택하면 출력 검증에서 거부한다. 점수로 피부 타입을 판정하지 않는다.
2015년 교육자료를 최신 임상 지침으로 표현하지 않는다.
원문 6개는 `doc/skin_guidelines/`, 생성 예시는 `examples/report.dry.fallback.json`에 있다.

## 3. 함수 하나로 호출

프로젝트 루트에서 실행하는 Python 코드:

```python
from backend.llm_service import generate_report

result = generate_report(analysis_data)  # 기본 auto: 키가 없거나 호출 실패 시 fallback
```

기존처럼 `backend` 폴더에서 `python test.py`를 실행하는 구성:

```python
from llm_service import generate_report

result = generate_report(analysis_data)
```

두 import 방식을 지원한다. 모듈 import만으로 Flask 서버, DB, 이미지 분석은 시작되지 않는다.

| mode | 동작 |
|---|---|
| `offline` | API를 절대 호출하지 않음 |
| `auto` | 환경변수 준비 시 한 번 호출. 실패 시 fallback |
| `llm` | 실제 LLM 결과만 성공 처리. 실패 시 `success: false`, `report: null` |

## 4. 반환 구조

```json
{
  "success": true,
  "report": {
    "summary": "종합 점수는 72점입니다. ...",
    "indicators": {
      "acne": "여드름 관련 감점은 35점입니다. ...",
      "pigmentation": "색소침착 관련 감점은 20점입니다. ...",
      "pore": "모공 관련 감점은 40점입니다. ...",
      "sebum": "피지 반사 관련 감점은 17점입니다. ..."
    },
    "care_tips": ["확인한 공식 자료의 일반 관리 안내"],
    "caution": "본 결과는 이미지 기반 참고 정보이며 의학적 진단을 대체하지 않습니다. ..."
  },
  "metadata": {
    "source": "fallback",
    "llm_success": false,
    "llm_attempted": false,
    "model": null,
    "prompt_version": "1.1.0",
    "knowledge_version": "2026-09-28.1",
    "warnings": [],
    "fallback_reason": "MISSING_API_KEY",
    "priority_indicators": ["pore"],
    "sources": []
  },
  "error": null
}
```

위는 설명용 축약 예시다. 실제 `sources`에는 사용한 자료의 제목·기관·URL·날짜·근거·관리 안내가 포함된다.
실행해서 저장한 전체 예시는 `examples/report.fallback.json`을 참고한다.

`success`는 사용 가능한 리포트 존재 여부다. 실제 LLM 성공 판단은 반드시
`metadata.source == "llm"` 및 `llm_success == true`로 한다.
입력 오류는 `error.code == "INVALID_INPUT"`, `source == "none"`, `report == null`이다.
잘못된 입력으로 대체 피부 상태를 지어내지 않는다.

## 5. 기존 Flask API와 DB 연결 위치 — 제안 코드

다음은 백엔드 담당자가 적용할 예시이며 기존 API에는 아직 반영하지 않았다.
`/analyze-skin`에서 `scores`, `total_score`, `raw_values`를 계산한 뒤, DB 트랜잭션을 열기 전에 생성한다.

```python
analysis_data = {
    "success": True,
    "total_score": total_score,
    "scores": scores,
    "raw_values": raw_values,
}
llm_result = generate_report(analysis_data)

# 기존 INSERT에 llm_report 컬럼과 바인딩 값 하나를 추가한다.
conn = sqlite3.connect(DB_PATH)
try:
    conn.execute("""
        INSERT INTO skin_analyses
        (user_id, score_total, score_acne, score_pore, score_pigmentation,
         score_sebum, raw_values, llm_report)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, total_score, scores["acne"], scores["pore"],
        scores["pigmentation"], scores["sebum"], json.dumps(raw_values),
        json.dumps(llm_result, ensure_ascii=False),
    ))
    conn.commit()
finally:
    conn.close()

# 기존 분석 응답 필드를 유지하고 별도 필드로 추가한다.
return jsonify({
    **analysis_data,
    "user_id": user_id,
    "llm_report": llm_result["report"],
    "llm_metadata": llm_result["metadata"],
    "llm_error": llm_result["error"],
}), 200
```

`llm_report TEXT` 컬럼은 이미 있으므로 새 컬럼은 필요 없다. 생성 방식까지 보존하려고
DB에는 전체 `llm_result`를 JSON 문자열로 저장한다. 읽을 때 `json.loads(row["llm_report"])`로 복원한다.
기존 INSERT 뒤 최신 행을 추측해서 UPDATE하지 말고 위처럼 같은 INSERT에 포함하는 것이 명확하다.
기존 `/history` SELECT에는 `llm_report`가 빠져 있으므로 기록 화면 연결 시 백엔드 담당자가 추가해야 한다.
LLM 호출은 동기식이며 HTTP 타임아웃은 30초, SDK 자동 재시도는 0회다.
운영 단계에서는 작업 큐·결과 캐시 도입을 검토한다.

Android의 `SkinAnalysisResponse.kt`에는 현재 리포트 필드가 없다.
프론트엔드 담당자는 `llm_report`, `llm_metadata`를 nullable 필드로 추가하고,
`ReportScreen.kt`의 고정 문구를 `summary`, `indicators`, `care_tips`, `caution`으로 연결하면 된다.
`source=fallback`이면 ‘기본 안내’, `source=llm`이면 ‘AI 생성 안내’처럼 구분한다.
현재 앱까지 자동 연결된 것은 아니며 점수/리포트 표시 및 화면 전환 통합 테스트가 남아 있다.

## 6. 실제 OpenAI API 실행

키는 이 대화나 소스 파일에 붙여 넣지 않는다. 아래는 터미널에서 숨김 입력을 받는 방식이다.

```powershell
$mirrorMeKey = Read-Host 'OpenAI API key' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $mirrorMeKey).Password
Remove-Variable mirrorMeKey
$env:OPENAI_MODEL = 'gpt-4.1-mini'
.\.venv\Scripts\python.exe -m backend.llm_service --mode llm --output report.live.json
```

모델은 환경변수로 교체 가능하다. 위 모델은 예시이며 계정에서 사용 가능한 Responses API /
Structured Outputs 지원 모델을 사용한다. API 키만으로는 충분하지 않고 `OPENAI_MODEL`도 설정해야 한다.
[모델 공식 문서](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[Structured Outputs 공식 문서](https://developers.openai.com/api/docs/guides/structured-outputs)를 참고했다.

실제 호출에는 비용이 발생할 수 있다. 위 명령은 한 번의 API 요청만 보낸다.
정상 완료 시 `success: true`, `source: "llm"`, `llm_success: true` 및 종료 코드 0이 기대 결과다.
이 모드는 fallback으로 성공을 숨기지 않는다. 키가 없으면 `MISSING_API_KEY`와 종료 코드 1이다.
호출 후 필요하면 `Remove-Item Env:OPENAI_API_KEY`로 현재 터미널 환경변수를 제거한다.

`.env.example`은 설정 항목 안내용이다. `.env` 자동 로드는 구현하지 않았다.
`.env` 및 `.env.*`, 로컬 리포트 파일은 `.gitignore`에 제외되어 있다.
실제 데이터 파일을 다른 이름으로 저장하면 직접 Git 포함 여부를 확인해야 한다.
API 요청에 `store=False`를 설정하지만 이를 외부 서비스의 모든 보관 정책에 대한 보장으로 해석하면 안 된다.

## 7. 테스트

무료 로컬 테스트만:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_llm_service.py' -v
```

전체 테스트 검색(실제 API 테스트는 기본 skip):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_llm*.py' -v
```

SDK의 실제 직렬화/파싱/오류 변환을 HTTP 모의 응답으로 검증한다.
이는 원격 OpenAI 서버나 실제 생성 품질 검증을 대체하지 않는다.
백엔드 폴더에서 직접 import하는 별도 Python 프로세스와 기존 SQLite 테이블 정의를 이용한
메모리 DB 저장·복원 테스트도 포함한다. 팀원의 실제 DB에는 쓰지 않는다.

별도의 유료 실제 API 테스트(앞의 키·모델 설정 후에만, CLI 호출과 중복 실행할 필요 없음):

```powershell
$env:RUN_LIVE_LLM_TEST = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_llm_live.py' -v
Remove-Item Env:RUN_LIVE_LLM_TEST
```

## 8. 오류 계약

| 상황 | 코드/처리 |
|---|---|
| 잘못된 입력 | `INVALID_INPUT`, 리포트 없음 |
| 잘못된 mode | `INVALID_MODE`, 리포트 없음 |
| KB 파일 손상 | `KNOWLEDGE_ERROR`, 리포트 없음 |
| 키·모델 누락 | `MISSING_API_KEY`, `MISSING_MODEL` |
| SDK 미설치 | `SDK_MISSING` |
| 네트워크·타임아웃 | `NETWORK_ERROR`, `TIMEOUT` |
| 인증·권한·한도 | `AUTHENTICATION_ERROR`, `ACCESS_DENIED`, `RATE_LIMIT` |
| 거절·불완전 응답 | `MODEL_REFUSAL`, `INCOMPLETE_RESPONSE` |
| JSON·내용 검증 실패 | `INVALID_JSON`, `INVALID_OUTPUT` |
| 그 밖의 외부 예외 | `UNEXPECTED_PROVIDER_ERROR` |

API 관련 오류는 `auto`에서 `fallback_reason`에 기록하고 대체 리포트를 반환한다.
`llm` 모드에서는 같은 코드를 `error.code`로 반환한다. 비밀값이 섞일 수 있는 원래 예외 메시지는 반환하지 않는다.
