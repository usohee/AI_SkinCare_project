# Mirror Me 백엔드

Flask 기반 REST API. 사진 한 장을 받아 피부 점수를 계산하고(OpenCV), LLM 리포트를 붙여 DB(SQLite)에 저장한다.

## 폴더 구조

```text
backend/
├── main.py                  # 서버 실행 진입점  (python main.py)
├── requirements.txt        # 패키지 목록
├── .env.example            # 환경변수 예시 (.env 로 복사해서 사용, GitHub에는 올리지 않음)
├── llm_service.py          # LLM 리포트 생성 (LLM 담당 모듈 — 수정하지 않음)
├── llm/                    # LLM 프롬프트·지식베이스·검증
├── app/
│   ├── __init__.py         # create_app(): 앱 생성, DB 초기화, 라우트 등록
│   ├── config.py           # 설정 + .env 로드
│   ├── db.py               # 테이블 정의, DB 연결
│   ├── routes/
│   │   ├── auth.py         # 회원가입 / 로그인 / 프로필
│   │   ├── analysis.py     # 피부 분석  POST /analyze-skin
│   │   ├── history.py      # 분석 기록  GET /history/<user_id>
│   │   ├── products.py     # 제품 검색 / 일괄 등록
│   │   ├── cabinet.py      # 내 화장대(소장 제품)
│   │   ├── health.py       # 서버 상태  GET /health
│   │   └── demo.py         # 시연 전용 (/demo, /app, /demo/seed)
│   ├── services/
│   │   └── skin_analyzer.py  # 피부 분석 알고리즘 (전처리·탐지·점수 계산)
│   └── static/             # 시연 대시보드 페이지
├── demo/                   # 오프라인 시연 화면(mirrorme_demo.html)과 준비 스크립트
├── tools/
│   └── validate_algorithm.py  # 장비 실측 대비 오차율 검증 (서버와 별개)
└── tests/                  # 자동 테스트  (python -m pytest -q)
```

## 실행 (Windows PowerShell)

```powershell
cd backend
python -m venv venv                 # 처음 한 번
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env              # 처음 한 번 → .env 에 OPENAI_API_KEY 입력 (없으면 규칙 기반 리포트)
python main.py                       # http://127.0.0.1:5000
```

서버가 켜졌는지: 브라우저에서 http://127.0.0.1:5000/health

## 테스트

```powershell
python -m pytest -q
```

## API 요약

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/signup` | 회원가입 `{email, password, nickname}` |
| POST | `/login` | 로그인 → `user_id`, `nickname` |
| GET/PUT | `/users/<user_id>/profile` | 프로필 조회/수정 |
| POST | `/analyze-skin` | form-data: `image`(파일), `user_id` → 점수 + `llm_report` + `llm_metadata` |
| GET | `/history/<user_id>` | 분석 기록 (오래된 순). 각 항목에 `llm_report`, `llm_metadata` 포함 |
| GET | `/products?q=` | 제품 검색 |
| POST | `/products/bulk-import` | 제품 일괄 등록 (같은 이름+브랜드는 건너뜀) |
| POST/GET | `/users/<user_id>/cabinet` | 소장 제품 등록 / 목록. `routine_time`: MORNING / NIGHT / ALL / NONE |
| GET | `/health` | 서버 상태, LLM 키 설정 여부 |

점수 의미: 항목 점수(acne, pore, pigmentation, sebum)는 **감점**(낮을수록 양호), `total_score`는 높을수록 양호.
`created_at`은 UTC로 저장된다(화면에서 KST로 변환).

## LLM 리포트

`backend/.env`에 `OPENAI_API_KEY`, `OPENAI_MODEL`이 둘 다 있으면 OpenAI로 생성한다.
키가 없거나 호출이 실패하면 규칙 기반 리포트로 자동 대체되고, `llm_metadata.source`가 `fallback`, `fallback_reason`에 사유가 담긴다.

## 시연 도구

- `GET /demo` — 대시보드형 시연 화면
- `GET /app` — 앱 UI 재현 화면 (`demo/mirrorme_demo.html`)
- `POST /demo/seed` — 시연 계정(`demo@mirrorme.com` / `demo1234`)의 기록을 초기 4건으로 되돌린다
- 오프라인 시연 파일 준비: `demo/` 폴더에서 `python embed_sample.py`
