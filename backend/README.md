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
│   │   ├── products.py     # 제품 검색 / 일괄 등록 / 제품 이미지
│   │   ├── cabinet.py      # 내 화장대(소장 제품)
│   │   ├── health.py       # 서버 상태  GET /health
│   │   └── demo.py         # 시연 전용 (/demo, /app, /demo/seed)
│   ├── services/
│   │   ├── skin_analyzer.py  # 피부 분석 알고리즘 (전처리·탐지·점수 계산)
│   │   ├── recommender.py    # 점수에 맞는 제품 고르기
│   │   ├── report_text.py    # LLM 리포트 → 앱에 보일 글
│   │   └── product_image.py  # 제품 이미지 생성
│   └── static/             # 시연 대시보드 페이지
├── demo/                   # 오프라인 시연 화면(mirrorme_demo.html)과 준비 스크립트
├── tools/
│   ├── import_products.py     # 제품 엑셀 → DB (python tools/import_products.py)
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
| POST | `/analyze-skin` | form-data: `image`(파일), `user_id` → 점수 + 리포트 + 추천 제품 (아래 참고) |
| GET | `/history/<user_id>` | 분석 기록. 기본 **최신순**, `?order=asc` 이면 오래된 순 |
| GET | `/products?q=` | 제품 검색 |
| POST | `/products/bulk-import` | 제품 일괄 등록 (같은 이름+브랜드는 건너뜀) |
| GET | `/product-image/<p제품번호 또는 t-종류>` | 제품 이미지(PNG). 서버가 만들어 준다 |
| POST/GET | `/users/<user_id>/cabinet` | 소장 제품 등록 / 목록. `routine_time`: MORNING / NIGHT / ALL / NONE |
| GET | `/health` | 서버 상태, LLM 제공자와 설정 여부 |

### 분석 응답 (`/analyze-skin`, `/history` 항목과 같은 모양)
```json
{
  "success": true, "user_id": "...", "date": "2026-10-29",
  "total_score": 56,
  "scores": {"acne": 14, "pigmentation": 59, "pore": 91, "sebum": 10},
  "llm_report": "종합 점수는 56점입니다. ...\n\n■ 항목별 결과\n• ...\n\n■ 관리 팁\n• ...\n\n※ ...",
  "llm_report_data": {"summary": "...", "indicators": {...}, "care_tips": [...], "caution": "..."},
  "llm_metadata": {"source": "llm | fallback", "provider": "anthropic | openai | null", "model": "..."},
  "recommendations": [
    {"name": "...", "brand": "...", "category": "세럼", "reason": "모공 관련 · 전성분에 ... 포함",
     "image_url": "http://<서버 주소>/product-image/p104"}
  ]
}
```
- `llm_report`는 앱 말풍선에 그대로 보여 줄 수 있는 **글(문자열)**이다. 같은 내용을 항목별로 쓰려면 `llm_report_data`를 쓴다.
- `/history` 항목에는 위 필드에 더해 `score_total`, `score_acne` … `created_at`(UTC) 같은 기존 필드도 들어 있다.
- 항목 점수는 **감점**(낮을수록 양호), `total_score`는 높을수록 양호. `date`는 한국 시간 기준.
- 제품 추천은 **전성분에 관련 성분이 들어 있는지**만 근거로 하며 효능을 보장하지 않는다. `products` 테이블이 비어 있으면 기본 제품 3개가 나온다.
- 제품 사진: 데이터셋에 사진이 없어 서버가 종류별 일러스트를 만든다. 실제 사진은 `app/static/products/<제품번호>.jpg`로 넣으면 자동으로 우선 사용한다.

### 제품 데이터 넣기 (처음 한 번)
```powershell
python tools\import_products.py
```
`dataset/skincare_products_data/`의 엑셀(약 200개 제품)을 DB에 넣는다. 여러 번 실행해도 중복되지 않는다.

## LLM 리포트

`backend/.env`에 키와 모델을 넣으면 해당 LLM으로 리포트를 만든다. (기본은 Claude)

| 제공자 | 환경변수 |
|---|---|
| Claude (기본) | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| OpenAI (예비) | `OPENAI_API_KEY`, `OPENAI_MODEL`, 그리고 `LLM_PROVIDER=openai` |

`LLM_PROVIDER`를 적지 않으면 `ANTHROPIC_API_KEY`가 있을 때 Claude, 없으면 OpenAI를 쓴다.
키가 없거나 호출이 실패하면 규칙 기반 리포트로 자동 대체되고, `llm_metadata`에 `source: "fallback"`과 `fallback_reason`(실패 사유)이 담긴다.
AI가 생성했다면 `source: "llm"`, `provider: "anthropic" | "openai"`.

설정 확인: `GET /health` → `llm_provider`, `llm_configured`

## 시연 도구

- `GET /demo` — 대시보드형 시연 화면
- `GET /app` — 앱 UI 재현 화면 (`demo/mirrorme_demo.html`)
- `POST /demo/seed` — 시연 계정(`demo@mirrorme.com` / `demo1234`)의 기록을 초기 4건으로 되돌린다
- 오프라인 시연 파일 준비: `demo/` 폴더에서 `python embed_sample.py`
