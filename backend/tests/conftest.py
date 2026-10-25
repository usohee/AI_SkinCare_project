import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def _no_llm_key(monkeypatch):
    # 테스트는 실제 OpenAI를 호출하지 않는다 → 규칙 기반 리포트로 동작
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)


@pytest.fixture()
def client(tmp_path):
    app = create_app({"DB_PATH": str(tmp_path / "test.db"), "TESTING": True})
    return app.test_client()


@pytest.fixture()
def jpeg_bytes():
    import cv2
    rng = np.random.default_rng(0)
    img = np.full((320, 320, 3), (150, 170, 200), np.uint8)
    cv2.circle(img, (160, 160), 100, (170, 190, 230), -1)
    noise = rng.integers(-12, 12, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()
