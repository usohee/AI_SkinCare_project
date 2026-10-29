"""앱(Android)이 기대하는 응답 모양, 추천 제품, 제품 이미지, 리포트 글 만들기 테스트."""
import io

import pytest

from app.services.recommender import pick_concerns
from app.services.report_text import format_report_text

REPORT = {
    "summary": "종합 점수는 36점입니다.",
    "indicators": {"acne": "여드름 관련 감점은 34점입니다.", "pigmentation": "색소침착 관련 감점은 100점입니다.",
                   "pore": "모공 관련 감점은 100점입니다.", "sebum": "피지 반사 관련 감점은 22점입니다."},
    "care_tips": ["보습제를 사용하세요.", "자외선차단제를 확인하세요."],
    "caution": "본 결과는 참고 정보입니다.",
}


def test_report_text_is_readable_not_a_dict_dump():
    text = format_report_text(REPORT)
    assert "{" not in text and "'summary'" not in text
    assert text.startswith("종합 점수는 36점입니다.")
    assert "■ 항목별 결과\n• 여드름 관련" in text and "■ 관리 팁\n• 보습제" in text and text.rstrip().endswith("참고 정보입니다.")
    assert format_report_text(None) is None and format_report_text({}) is None


def test_pick_concerns():
    assert pick_concerns({"acne": 10, "pigmentation": 5, "pore": 90, "sebum": 40}) == ["pore", "sebum"]
    assert pick_concerns({"acne": 1, "pigmentation": 2, "pore": 3, "sebum": 4}) == ["sebum"]   # 모두 낮으면 가장 큰 항목 하나


def _import(client):
    products = [
        {"product_name": "시카 세럼", "brand": "A", "ingredients": "정제수, 병풀추출물, 마데카소사이드, 티트리잎오일", "category": "세럼"},
        {"product_name": "BHA 토너", "brand": "B", "ingredients": "정제수, 살리실산, 나이아신아마이드, 녹차추출물", "category": "토너"},
        {"product_name": "비타민 크림", "brand": "C", "ingredients": "정제수, 아스코빅애씨드, 알부틴, 나이아신아마이드", "category": "크림"},
        {"product_name": "무관한 로션", "brand": "D", "ingredients": "정제수, 글리세린", "category": "로션"},
    ]
    assert client.post("/products/bulk-import", json={"products": products}).status_code == 201


def test_recommendations_follow_scores(client):
    from app import create_app  # noqa: F401  (client fixture가 앱을 만든다)
    _import(client)
    # 직접 점수를 넣는 대신 분석 → 기록 경로로 확인: 시드 기록(여드름·모공 위주)에도 추천이 붙는다
    client.post("/demo/seed")
    hist = client.get("/history/demo-user").get_json()["history"]
    names = [r["name"] for r in hist[0]["recommendations"]]
    assert 1 <= len(names) <= 3 and "무관한 로션" not in names
    for r in hist[0]["recommendations"]:
        assert r["brand"] and r["reason"] and r["image_url"].endswith(tuple("0123456789"))
        assert r["image_path"].startswith("/product-image/p")


def test_fallback_recommendations_when_no_products(client):
    client.post("/demo/seed")
    recs = client.get("/history/demo-user").get_json()["history"][0]["recommendations"]
    assert recs and all(r["image_path"].startswith("/product-image/t-") for r in recs)


def test_product_images(client):
    _import(client)
    pid = client.get("/products?q=시카").get_json()["products"][0]["product_id"]
    ok = client.get(f"/product-image/p{pid}")
    assert ok.status_code == 200 and ok.mimetype == "image/png" and ok.data[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get("/product-image/t-cream").status_code == 200
    assert client.get("/product-image/t-unknown").status_code == 200       # 모르는 종류는 기본 일러스트
    assert client.get("/product-image/p99999").status_code == 404
    assert client.get("/product-image/evil").status_code == 404
    # /products 목록도 서버가 만든 이미지 주소를 채워 준다
    item = client.get("/products?q=시카").get_json()["products"][0]
    assert item["image_url"].endswith(f"/product-image/p{pid}")


def test_analyze_response_matches_app_model(client, jpeg_bytes):
    r = client.post("/analyze-skin", data={"image": (io.BytesIO(jpeg_bytes), "a.jpg"), "user_id": "app-user"},
                    content_type="multipart/form-data")
    b = r.get_json()
    # 앱 SkinAnalysisResponse: success, user_id, date, total_score, scores{4}, llm_report(String), recommendations[{name, brand, image_url}]
    assert b["success"] is True and isinstance(b["total_score"], int) and isinstance(b["llm_report"], str)
    assert len(b["date"]) == 10 and set(b["scores"]) == {"acne", "pigmentation", "pore", "sebum"}
    assert all({"name", "brand", "image_url"} <= set(x) for x in b["recommendations"])
    h = client.get("/history/app-user").get_json()["history"][0]
    assert h["date"] == b["date"] and h["llm_report"] == b["llm_report"]
    assert [x["name"] for x in h["recommendations"]] == [x["name"] for x in b["recommendations"]]


def test_import_products_tool(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    import sqlite3
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "tools"))
    import import_products

    xlsx = tmp_path / "p.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"
    ws.append(["product_id", "brand", "product_name", "product_type", "ingredients_raw"])
    ws.append(["P1", "A", "시카 세럼", "세럼", "정제수, 병풀추출물"])
    ws.append(["P2", "B", "BHA 토너", "토너", "정제수, 살리실산"])
    wb.save(xlsx)
    db = tmp_path / "t.db"
    for expected in ((2, 0), (0, 2)):                      # 두 번 실행해도 중복되지 않는다
        sys.argv = ["import_products.py", "--xlsx", str(xlsx), "--db", str(db)]
        import_products.main()
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM products").fetchone()[0]
    assert n == 2
