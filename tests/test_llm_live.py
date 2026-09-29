"""명시적으로 허용한 경우에만 실제 API를 한 번 호출한다."""
import json
import os
from pathlib import Path
import unittest
from backend.llm_service import generate_report


@unittest.skipUnless(os.getenv("RUN_LIVE_LLM_TEST") == "1", "실제 API 테스트는 RUN_LIVE_LLM_TEST=1로 별도 실행")
class LiveLLMTest(unittest.TestCase):
    def test_real_llm_report(self):
        self.assertTrue(os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY 미설정")
        self.assertTrue(os.getenv("OPENAI_MODEL"), "OPENAI_MODEL 미설정")
        data = json.loads((Path(__file__).resolve().parents[1] / "examples/analysis.json").read_text(encoding="utf-8"))
        result = generate_report(data, mode="llm")
        self.assertTrue(result["success"], result["error"])
        self.assertTrue(result["metadata"]["llm_success"])
        self.assertEqual(result["metadata"]["source"], "llm")


if __name__ == "__main__":
    unittest.main()
