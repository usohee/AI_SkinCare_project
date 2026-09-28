# Mirror Me — AI 프롬프트 엔지니어링 파트

## 목적과 범위

이미지 분석 팀이 계산한 피부 수치를 사용자가 이해할 수 있는 한국어 참고 리포트로 변환한다.
담당 기능은 입력 검증, 수치 해석, 프롬프트 설계, 공식 자료 선택, LLM 호출, 응답 검증과 fallback이다.
이미지 분석 알고리즘, Android UI, 회원 인증 API는 이번 작업 범위에 포함하지 않는다.

## 기존 프로젝트 확인 결과

- 서버는 `backend/test.py`의 Flask이며 SQLite를 사용한다.
- `/analyze-skin`은 `success`, `user_id`, `total_score`, `scores`, `raw_values`를 반환한다.
- 분석 항목은 여드름·색소침착·모공·피지 반사다. README의 홍조/YOLO 설명과 실제 코드가 다르다.
- 개별 감점은 `min(100, int(raw / MAX_VALUES * 100))`이다.
- `MAX_VALUES`는 acne=50, pigmentation=250, pore=27.0, sebum=0.6이다.
- 종합 점수는 `max(0, 100 - round(sum(scores.values()) / len(scores)))`이다.
- `skin_analyses.llm_report TEXT`는 이미 존재하지만 기존 API는 여기에 저장하지 않는다.
- Android `SkinAnalysisResponse`는 점수/원시값만 받고, `ReportScreen`의 조언·추천·추이는 고정 예시다.
- 기존 LLM 시작 파일, 연동 문서, 테스트는 없었다. 이번에 독립 모듈로 추가했다.
- 이 작업 폴더에는 `.git`이 없어 Git 변경 내역 비교는 불가능했다. 기존 서버/Android 파일은 편집하지 않았으며 commit/push도 하지 않았다.

## 처리 흐름과 구조 선택 이유

```text
분석 JSON
  → 입력 검증 + 개인정보 제거
  → 계산식과 점수 방향을 반영한 사실 문장 생성
  → 상위 감점 두 항목에서 각 최대 2개 + 공통 3개 + 자기보고 유형 최대 1개 선택
  → system/user 프롬프트 분리
  → 공식 OpenAI SDK Responses API + 엄격한 JSON Schema
  → 구조·사실 문장·추가 주장·자료 ID 검증
  → report + metadata 반환
       실패하면 auto 모드에서만 규칙 기반 fallback
```

검증과 해석을 LLM 호출보다 먼저 수행하므로 잘못된 입력에 비용을 쓰지 않는다.
점수와 방향을 모델의 자유 생성에 맡기지 않고 사실 문장으로 고정한다.
모델은 사실 문장 뒤의 짧은 설명을 생성하고, 관련 관리 안내 ID를 선택한다.
실제 관리 문구와 출처는 검증된 KB에서 가져온다. 이렇게 하면 존재하지 않는 치료법·출처를
생성하는 위험을 줄이면서도 수치·우선 항목에 맞는 리포트를 만들 수 있다.

## 파일별 역할

| 파일 | 역할 |
|---|---|
| `llm_service.py` | 공개 함수와 CLI, 호출 방식·오류·fallback 제어 |
| `llm/contracts.py` | 입력 검증, 개인 식별 필드 제거, 수치 해석 |
| `llm/prompts.py` | system/user 프롬프트와 JSON Schema |
| `llm/provider.py` | SDK 호출, 타임아웃·재시도·오류 분류 |
| `llm/output.py` | 출력 검증, 규칙 기반 리포트 |
| `llm/knowledge.py` | 관련 자료 선택과 출처 메타데이터 |
| `llm/knowledge_base.json` | 근거 자료와 관리 문구, 확인 상태 |
| `../tests/test_llm_service.py` | 무료 로컬/SDK 모의/호출·DB 계약 테스트 |
| `../tests/test_llm_live.py` | 명시적으로 켠 경우만 실제 API 테스트 |
| `../examples/analysis.json` | 개인정보 없는 임시 분석 입력 |
| `../examples/report.fallback.json` | 실제 로컬 실행으로 생성한 결과 |
| `../requirements-llm.txt` | 검증한 OpenAI SDK 버전 |
| `../.env.example` | 필요한 환경변수 이름 안내 |
| `../INTEGRATION.md` | 입력·출력 계약, PowerShell 실행, 서버/DB/Android 연동 |

Python 3.12.10, OpenAI Python SDK 2.54.0으로 검증했다. 로컬 생성은 표준 라이브러리만 사용한다.
OpenAI SDK는 실제 호출 경로에서만 import하여 다른 팀의 Flask/OpenCV 실행과 분리했다.

## 프롬프트 설계

System Prompt는 한국어 리포트 작성 역할, 네 분석 항목, 반대인 점수 방향, 의료 진단 금지,
피부 타입 추정 금지, 원인·치료 효능 창작 금지, JSON 출력 규칙을 정의한다.
User Prompt는 검증된 수치, 선택적 자기보고 유형, 사실 문장, 선택된 KB 항목과 적용 한계를 포함한다.
이메일/사용자 ID/사진/프로필 자유문은 전달하지 않는다. 프롬프트 입력으로 명령을 주입할 자유문 필드도 받지 않는다.
LLM 출력은 내부적으로 `summary`, `indicators`, `care_tip_ids`이며, 최종 API 반환 전
`care_tip_ids`를 확인된 `care_tips` 문구로 변환하고 고정 `caution`을 추가한다.

지표가 모두 같으면 특정 지표가 더 문제라고 주장하지 않는다. 모두 0이어도 문제가 없다고 진단하지 않는다.
감점의 상대적 크기는 알고리즘상 비교이며 실제 피부 질환 중증도 비교로 해석하지 않는다.

## 지식 베이스

2026-09-28에 원문 6개를 확인·저장했다. 전문 진료지침 전체가 아니라 소비자용 일반 관리 안내의 제한된 요약이다.
각 항목은 자료명, 기관, URL, 발행/개정일, 확인일, 관련 지표, 근거 요약, 적용 문구를 포함한다.
발행·개정일을 확인할 수 없는 AAD 자료는 `null`과 설명을 남겼다.

| 자료 | 사용 내용 |
|---|---|
| [대한피부과의사회 피부 고민 해결!](https://akd.or.kr/dermatologist/why) | 전문의 상담과 임의의 자가 관리 주의 |
| [식약처 자외선차단제 안내, 2026-06-05](https://www.korea.kr/news/policyNewsView.do?newsId=148965990) | 자외선 관련 관리·표시 확인 |
| [AAD Acne: Tips for managing](https://www.aad.org/public/diseases/acne/skin-care/tips) | 자극을 줄이는 세안 |
| [AAD What can treat large facial pores?](https://www.aad.org/public/everyday-care/skin-care-secrets/face/treat-large-pores) | 부드러운 세안·모공을 짜지 않기 |
| [AAD How to control oily skin](https://www.aad.org/public/everyday-care/skin-care-basics/dry/oily-skin) | 순한 세정·보습 안내. 지성 진단에 사용하지 않음 |

대한피부과의사회 공식 홈페이지에서 원문을 확인하여 `akd_professional_guidance`로 추가했다.
본문 발행·개정일은 표시되지 않아 `null`로 기록했다. Copyright 연도를 발행일로 사용하지 않았다.
일반 상담 안내로 프롬프트와 fallback 리포트에 반영한다. 구체적인 세안·보습 방법의 근거로 확장하지 않는다.
`pending_sources`에는 해당 기관의 구체적인 관리법 자료 추가 확보만 남겨 두었다.
원문 확인 범위와 적용 근거는 [AKD_SOURCE_NOTES.md](llm/AKD_SOURCE_NOTES.md)에 기록했다.
식약처와 대한피부과의사회 모든 가이드라인을 준수한다는 주장은 하지 않는다.

자료 추가 시 원문을 확인한 후 새 ID와 메타데이터를 입력하고 `verified=true`로 설정한다.
`general=true`는 모든 분석에 공통으로 넣을 때만 사용한다. 기타 자료는 관련 지표가 상위 두 항목에 포함될 때 선택한다.
동점 정렬은 acne/pigmentation/pore/sebum 순서로 안정적으로 처리하며 이는 의학적 우선순위가 아니다.
런타임에는 웹 크롤링이나 벡터 DB가 필요 없다. 작은 KB에 맞는 단순 선택 구조로 유지보수와 비용을 줄였다.

## 완료한 것과 남은 것

구현 및 로컬 검증: 입력 JSON→리포트, 점수 방향, 선택적 KB, SDK 요청 형식,
예외/fallback, 개인정보 배제, 모듈 import, 기존 DB 스키마에 JSON 저장·복원.

미완료/미검증:

- API 키가 없어 실제 LLM 생성 성공과 생성 문장 품질은 미검증이다.
- 기존 Flask API와 Android에는 연결하지 않았다. 연동 지점과 예시 코드는 INTEGRATION.md에 있다.
- 대한피부과의사회 상담·자가 관리 주의 원문은 반영 완료. 해당 기관의 구체적인 세안·보습 등 관리법 원문 추가 확보는 남아 있다.
- 출력 검증은 JSON 구조, 고정 사실 문장, 허용 자료 ID, 알려진 위험 표현을 검사한다.
  임의의 한국어 문장에 포함된 모든 의미 오류를 완벽하게 판별하지는 못한다.
  라이브 결과에 대한 사람이 하는 검토와 여러 입력을 이용한 품질 평가가 필요하다.
- 상용 의료 정확도/임상 검증, 개인별 알레르기·제품 적합성·성분 추천, 과거 기록 해석은 구현하지 않았다.
- 원시 측정값과 감점의 일관성 검증은 알고리즘 팀과 계약 확정 후 보강할 수 있다.

실제 실행 명령과 기대 출력은 [INTEGRATION.md](../INTEGRATION.md), 실행 결과는 [TEST_RESULTS.md](../TEST_RESULTS.md)를 참고한다.


## 2026-09-28 상세 관리 보강

대한피부과학회의 「피부관리」(2015-12-21) 교육자료를 추가했다. 대한피부과의사회와 다른 기관이며 최신 임상 지침이 아니다.
`self_reported_skin_type`이 dry/oily/combination_oily일 때 해당 유형의 일반 관리만 선택한다.
생략/null/unknown이면 유형 자료를 선택하지 않는다. 알고리즘의 skin_type과 피지 점수로 유형을 추정하지 않는다.
자기보고를 참고한 조건부 안내 문구만 제공하고, 자유 생성 문장에서는 피부 타입을 진단하지 못하도록 기존 검증을 유지했다.
지표별 자료는 상위 두 항목에서 각 최대 2개, 공통 3개, 유형 최대 1개로 선택량을 제한한다.
여드름의 세안·손으로 짜지 않기, 모공 제품 표시, 식약처 자외선차단제 사용법도 보강했다.
원문 HTML·발행일·적용 범위·파일 해시는 [doc/skin_guidelines](../doc/skin_guidelines/README.md)에 있다.
기존 알레르기·성분·제품 적합성 판단 및 실제 LLM 검증은 여전히 범위 밖/미검증이다.
