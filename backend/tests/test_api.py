"""API 스모크 테스트.  backend 폴더에서:  python -m pytest -q"""
import io


def _post_image(client, data, user_id="u1"):
    return client.post(
        "/analyze-skin",
        data={"image": (io.BytesIO(data), "a.jpg"), "user_id": user_id},
        content_type="multipart/form-data",
    )


def test_health(client):
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["llm_configured"] is False


def test_signup_login_profile(client):
    r = client.post("/signup", json={"email": "a@b.com", "password": "pw1234", "nickname": "예진"})
    assert r.status_code == 201
    uid = r.get_json()["user_id"]

    assert client.post("/signup", json={"email": "a@b.com", "password": "x"}).status_code == 409
    assert client.post("/signup", json={"email": "bad", "password": "x"}).status_code == 400

    ok = client.post("/login", json={"email": "a@b.com", "password": "pw1234"})
    assert ok.status_code == 200 and ok.get_json()["nickname"] == "예진"
    assert client.post("/login", json={"email": "a@b.com", "password": "wrong"}).status_code == 401
    assert client.post("/login", json={}).status_code == 401

    put = client.put(f"/users/{uid}/profile", json={"skin_type": "oily", "skin_concern": ["여드름"]})
    assert put.status_code == 200
    prof = client.get(f"/users/{uid}/profile").get_json()["profile"]
    assert prof["skin_concern"] == ["여드름"]
    assert "password_hash" not in prof
    assert client.get("/users/none/profile").status_code == 404


def test_analyze_and_history(client, jpeg_bytes):
    r = _post_image(client, jpeg_bytes)
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] and body["user_id"] == "u1"
    assert set(body["scores"]) == {"acne", "pore", "pigmentation", "sebum"}
    assert 0 <= body["total_score"] <= 100
    assert isinstance(body["llm_report"], str) and "종합 점수는" in body["llm_report"]   # 앱 화면용 글
    assert body["llm_report_data"]["summary"]                                          # 구조화된 같은 내용
    assert body["llm_metadata"]["source"] == "fallback"
    assert body["recommendations"] and body["recommendations"][0]["image_url"].startswith("http://localhost/product-image/")

    _post_image(client, jpeg_bytes)
    hist = client.get("/history/u1").get_json()["history"]
    assert len(hist) == 2
    assert "종합 점수는" in hist[0]["llm_report"]         # /analyze-skin 과 같은 글
    assert hist[0]["llm_report_data"]["summary"]
    assert hist[0]["llm_metadata"]["source"] == "fallback"
    assert hist[0]["total_score"] == hist[0]["score_total"] and set(hist[0]["scores"]) == {"acne", "pigmentation", "pore", "sebum"}
    assert client.get("/history/nobody").get_json()["history"] == []


def test_analyze_bad_input(client):
    assert client.post("/analyze-skin", data={}, content_type="multipart/form-data").status_code == 400
    assert _post_image(client, b"").status_code == 400            # 빈 파일
    assert _post_image(client, b"not an image").status_code == 400


def test_products_and_cabinet(client):
    rows = [
        {"product_name": "Test Toner", "brand": "B", "ingredients": "Water, Glycerin", "category": "toner"},
        {"product_name": "Test Toner", "brand": "B"},            # 중복 → 건너뜀
        {"brand": "no-name"},                                    # 이름 없음 → 건너뜀
    ]
    imp = client.post("/products/bulk-import", json={"products": rows}).get_json()
    assert imp["inserted"] == 1 and imp["skipped"] == 2

    found = client.get("/products?q=Toner").get_json()["products"]
    assert len(found) == 1
    pid = found[0]["product_id"]

    assert client.post("/users/u1/cabinet", json={}).status_code == 400
    assert client.post("/users/u1/cabinet", json={"product_id": 999}).status_code == 404
    assert client.post("/users/u1/cabinet", json={"product_id": pid, "routine_time": "X"}).status_code == 400
    ok = client.post("/users/u1/cabinet", json={"product_id": pid, "routine_time": "MORNING"})
    assert ok.status_code == 201

    cab = client.get("/users/u1/cabinet").get_json()["cabinet"]
    assert len(cab) == 1 and cab[0]["product_name"] == "Test Toner" and cab[0]["routine_time"] == "MORNING"


def test_demo_seed_and_login(client):
    assert client.post("/login", json={"email": "demo@mirrorme.com", "password": "demo1234"}).status_code == 200
    seeded = client.post("/demo/seed").get_json()
    assert seeded["seeded"] == 4
    hist = client.get("/history/demo-user").get_json()["history"]
    assert [h["score_total"] for h in hist] == [62, 60, 57, 54]          # 최신순(앱 기본)
    asc = client.get("/history/demo-user?order=asc").get_json()["history"]
    assert [h["score_total"] for h in asc] == [54, 57, 60, 62]
    assert hist[0]["date"] and hist[0]["recommendations"]               # 예전 기록도 추천 제품이 채워진다
    assert client.get("/demo").status_code == 200
