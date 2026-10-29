"""샘플 사진과 실제 분석 결과를 mirrorme_demo.html 안에 넣는다 (오프라인 시연 준비용).

사용법 (backend/demo 폴더에서, 가상환경을 켠 상태)
    python embed_sample.py                  서버가 켜져 있으면: 샘플 사진을 서버로 분석해 결과까지 새로 기록
                                            서버가 꺼져 있으면: 샘플 사진만 넣고 기존 결과 유지
    python embed_sample.py --skip-record    사진만 넣는다 (서버 호출 안 함)
    python embed_sample.py --api http://127.0.0.1:5000

같은 사진(test_selfie.jpg)으로 분석한 서버의 실제 응답을 그대로 저장하므로,
오프라인으로 시연해도 '이 사진 → 이 결과'가 서버가 실제로 낸 값과 일치한다.
OpenAI 크레딧이 충전된 뒤에는 키를 설정한 서버로 이 명령을 다시 실행하면 AI 생성 리포트가 기록된다.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = next((p for p in (os.path.join(HERE, "test_selfie.jpg"), os.path.join(os.path.dirname(HERE), "test_selfie.jpg")) if os.path.exists(p)),
             os.path.join(os.path.dirname(HERE), "test_selfie.jpg"))
HTML = os.path.join(HERE, "mirrorme_demo.html")
RECORD_USER = "recording-user"  # 시연 계정과 섞이지 않도록 별도 사용자로 기록한다


def photo_bytes_small(path, max_side=480):
    """긴 변 480px JPEG로 줄여 HTML에 넣는다 (원본은 그대로 서버로 보낸다)."""
    try:
        import cv2
        img = cv2.imdecode(__import__("numpy").fromfile(path, dtype="uint8"), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("이미지를 읽을 수 없습니다")
        h, w = img.shape[:2]
        scale = max_side / max(h, w)
        if scale < 1:
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise ValueError("JPEG 변환 실패")
        return buf.tobytes()
    except ImportError:
        with open(path, "rb") as f:
            return f.read()


def post_image(api, path):
    boundary = "----mirrorme" + uuid.uuid4().hex
    with open(path, "rb") as f:
        data = f.read()
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="user_id"\r\n\r\n{RECORD_USER}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="test_selfie.jpg"\r\n'
         "Content-Type: image/jpeg\r\n\r\n").encode() + data + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        api.rstrip("/") + "/analyze-skin", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_recorded(resp):
    report = resp.get("llm_report_data") or (resp.get("llm_report") if isinstance(resp.get("llm_report"), dict) else {}) or {}
    meta = resp.get("llm_metadata") or {}
    scores = resp["scores"]
    return {
        "total": resp["total_score"],
        "acne": scores["acne"], "pore": scores["pore"],
        "pigmentation": scores["pigmentation"], "sebum": scores["sebum"],
        "report": {
            "summary": report.get("summary", ""),
            "care_tips": report.get("care_tips", []),
            "caution": report.get("caution", ""),
        },
        "meta": {"source": meta.get("source"), "model": meta.get("model")},
    }


def replace_between(text, name, new_code):
    pattern = re.compile(r"/\*%s_BEGIN\*/.*?/\*%s_END\*/" % (name, name), re.S)
    if not pattern.search(text):
        sys.exit(f"[오류] mirrorme_demo.html 에서 {name} 표시를 찾지 못했습니다. 원본 파일을 다시 받아 주세요.")
    return pattern.sub(lambda m: f"/*{name}_BEGIN*/{new_code}/*{name}_END*/", text, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:5000")
    ap.add_argument("--skip-record", action="store_true")
    args = ap.parse_args()

    for p in (PHOTO, HTML):
        if not os.path.exists(p):
            sys.exit(f"[오류] 파일이 없습니다: {p}  (샘플 사진은 backend/test_selfie.jpg 로 두세요)")

    with open(HTML, encoding="utf-8") as f:
        html = f.read()

    small = photo_bytes_small(PHOTO)
    data_url = "data:image/jpeg;base64," + base64.b64encode(small).decode("ascii")
    html = replace_between(html, "SAMPLE_PHOTO", "const SAMPLE_PHOTO = " + json.dumps(data_url) + ";")
    print(f"[완료] 샘플 사진을 넣었습니다 ({len(small) // 1024}KB)")

    if not args.skip_record:
        try:
            resp = post_image(args.api, PHOTO)
            if not resp.get("success"):
                raise RuntimeError(resp.get("message", "분석 실패"))
            rec = to_recorded(resp)
            html = replace_between(html, "RECORDED", "const RECORDED = " + json.dumps(rec, ensure_ascii=False, indent=2) + ";")
            src = rec["meta"]["source"]
            print(f"[완료] 서버 분석 결과를 기록했습니다: 종합 {rec['total']}점, "
                  f"여드름 {rec['acne']} / 모공 {rec['pore']} / 색소침착 {rec['pigmentation']} / 피지 {rec['sebum']}, "
                  f"리포트 출처: {src}")
        except (urllib.error.URLError, OSError, RuntimeError, KeyError, ValueError) as e:
            print(f"[알림] 서버 결과는 기록하지 못했습니다 ({e}). 사진만 넣었고 기존 결과를 유지합니다.")

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("[완료] mirrorme_demo.html 을 저장했습니다.")


if __name__ == "__main__":
    main()
