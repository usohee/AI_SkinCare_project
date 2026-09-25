# LLM 모듈 실행·검증 기록

검증일: 2026-09-25. 환경: Windows / Python 3.12.10 / OpenAI SDK 2.54.0.

## 요청한 세 가지 최종 확인

| 확인 사항 | 결과 | 실제 증거 |
|---|---|---|
| 임시 분석 JSON → 리포트 | 통과 | offline/auto CLI 실행 및 JSON 파일 저장 성공 |
| API 키 설정 → 실제 LLM 생성 | **미완료·미검증** | 환경에 OPENAI_API_KEY가 없어 원격 API 호출하지 않음 |
| 백엔드에서 간단히 호출 | 모듈 단위 통과 | backend 폴더의 별도 프로세스에서 import/호출, 기존 DB 스키마에 저장·복원 성공 |

Flask HTTP API 및 Android까지 이어지는 전체 서비스 통합은 이번 범위에서 수행하지 않았다.
서버 코드를 바꾸지 않고, 백엔드 담당자용 적용 예시를 INTEGRATION.md에 작성했다.

## 실제 실행한 명령과 결과

프로젝트 루트는 `C:\Users\xhflz\Downloads\AI_SkinCare_project-main\AI_SkinCare_project-main`이다.

1. `.\.venv\Scripts\python.exe -m backend.llm_service --mode offline --output report.local.json`
   - 종료 코드 0, `success=true`, `source=fallback`, `fallback_reason=OFFLINE_MODE`.
2. `python -m backend.llm_service --mode auto --output report.local.json`
   - SDK가 없는 기본 Python에서도 종료 코드 0.
   - API 키가 없어 `source=fallback`, `fallback_reason=MISSING_API_KEY`.
   - 이 실행 결과를 `examples/report.fallback.json`으로 복사했다.
3. `.\.venv\Scripts\python.exe -m backend.llm_service --mode llm`
   - 종료 코드 1, `success=false`, `report=null`, `error.code=MISSING_API_KEY`.
   - 실제 호출이 불가능한데 fallback을 LLM 성공으로 표시하지 않는 것을 확인했다.
4. `.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_llm*.py' -v`
   - **Ran 35 tests / OK (skipped=1)**. 34개 통과, 실제 API 테스트 1개 명시적 생략.
5. `.\.venv\Scripts\python.exe -m compileall -q backend/llm backend/llm_service.py tests`
   - 종료 코드 0.
6. `.\.venv\Scripts\python.exe -m pip check`
   - `No broken requirements found.`

DB 테스트가 기존 `backend/test.py`를 AST로 읽을 때 기존 563~564행의 `\l` 문자열에 대해
Python SyntaxWarning이 출력되었다. 테스트는 통과했으며 다른 팀원 소스는 수정하지 않았다.

## 입력과 출력

입력: 종합 72, 여드름 감점 35, 색소침착 감점 20, 모공 감점 40, 피지 반사 감점 17.

실제 summary:

> 종합 점수는 72점입니다. 종합 점수는 높을수록 양호한 방향입니다. 이번 분석에서는 모공 항목의 감점이 상대적으로 큽니다. 이는 질환의 중증도나 실제 문제 크기 순위가 아닙니다.

실제 pigmentation 설명:

> 색소침착 관련 감점은 20점입니다. 개별 점수는 높을수록 감점이 큽니다.

care_tips에는 검증한 자료에서 가져온 순한 세안, 모공을 세게 짜지 않기, 보습, 자외선 관리 안내가 포함된다.
전체 결과는 [examples/report.fallback.json](examples/report.fallback.json)에 있다.

## 테스트 범위

- 정상 dict/JSON 문자열, 선택 필드 생략, 필수 필드 누락, 잘못된 JSON.
- 점수 범위/정수/NaN/bool 검증, 잘못된 원시값과 매우 큰 값 검증.
- 종합·개별 점수 방향, 감점 동점·0점, 입력 변화에 따른 출력 변화.
- pigmentation과 홍조 구분, 알 수 없는 지표/틀린 점수/새 숫자·피부 타입 주장 거부.
- 공식 출처 선택, 개인정보·자유문 명령 배제, 원본 입력 보존.
- 키·모델 누락, 모드 오류, SDK 호출 성공/실패 구분, KB 읽기 실패.
- OpenAI SDK를 실제 실행하고 HTTP만 모의 처리: 구조화 요청, 응답 파싱, 401, 네트워크 오류,
  시간 초과, 잘못된 JSON, 거절, 불완전 응답.
- 별도 Python 프로세스에서 백엔드용 직접 import, 기존 SQLite 스키마에 JSON 저장·복원.

위 SDK 테스트는 실제 LLM 추론 테스트가 아니다. 모델의 지시 준수율, 자연스러운 표현,
원격 API의 모델 접근 권한, 과금 계정 상태, 실제 응답 시간은 검증하지 못했다.

## 다음 검증

1. 키와 OPENAI_MODEL 설정 후 `--mode llm`으로 합성 입력 한 건 호출.
2. `source=llm`, `llm_success=true`, 종료 코드 0인지 확인하고 생성 문장을 사람이 검토.
3. 여러 점수 조합에 대한 실제 출력 품질과 거부/fallback 비율 평가.
4. 팀원들이 Flask/DB/Android를 연결한 뒤 전체 흐름 검증.
5. 대한피부과의사회 구체적인 세안·보습 등 주제별 관리 자료 추가 확보. 상담 안내 원문은 아래 후속 검증에서 반영 완료.

## 후속 검증: 대한피부과의사회 자료 추가 (2026-09-25)

- 공식 원문 `https://akd.or.kr/dermatologist/why`를 직접 확인해 전문의 상담·자가 관리 주의 항목 추가.
- KB 버전 `2026-09-25.2`. 원문의 표시되지 않은 발행일은 추정하지 않고 null 유지.
- 프롬프트에 자료가 전달되고, fallback 리포트에 관리 문구와 원문 출처가 포함되는 테스트 추가.
- 전체 재실행: **Ran 36 tests / OK (skipped=1)** — 35개 통과, 실제 API 테스트 1개 생략.
- offline CLI로 `examples/report.fallback.json`을 다시 생성하여 상담 안내와 출처가 포함됨을 확인.
  이 파일은 위 초기 auto 실행본을 대체하며 현재 `fallback_reason=OFFLINE_MODE`이다.
- 실제 LLM 호출은 여전히 API 키 부재로 미검증. 구체적인 세안·보습 방법을 이 상담 안내 원문에서 도출하지 않음.
