"""제품 이미지를 서버가 직접 만들어 준다 (외부 쇼핑몰 이미지 주소에 의존하지 않기 위함).

데이터셋에는 제품 사진이 없으므로, 제품 종류별 일러스트(병/단지/튜브)를 OpenCV로 그린다.
실제 사진이 있으면 backend/app/static/products/<product_id>.jpg|png|webp 로 넣으면 자동으로 우선 사용한다.
"""
import cv2
import numpy as np

SIZE = 320
_SCALE = 2  # 2배로 그린 뒤 줄여서 가장자리를 부드럽게 한다

# 종류 → (배경색, 제품 색)  (BGR)
_PALETTE = {
    "toner": ((242, 247, 238), (176, 204, 140)),
    "cream": ((238, 242, 250), (150, 178, 226)),
    "serum": ((246, 240, 236), (200, 160, 130)),
    "cleanser": ((240, 246, 246), (150, 200, 210)),
    "mist": ((247, 244, 238), (210, 190, 150)),
    "default": ((244, 244, 244), (170, 170, 170)),
}

_KIND_WORDS = (
    ("cleanser", ("클렌", "폼", "워시")),
    ("mist", ("미스트",)),
    ("serum", ("세럼", "앰플", "에센스")),
    ("cream", ("크림", "로션", "에멀젼", "에멀전", "기초")),
    ("toner", ("토너", "스킨", "패드")),
)


def kind_for(category):
    text = str(category or "")
    for kind, words in _KIND_WORDS:
        if any(w in text for w in words):
            return kind
    return "default"


def _rrect(img, x1, y1, x2, y2, r, color):
    r = int(min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1, cv2.LINE_AA)
    cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1, cv2.LINE_AA)
    for cx, cy in ((x1 + r, y1 + r), (x2 - r, y1 + r), (x1 + r, y2 - r), (x2 - r, y2 - r)):
        cv2.circle(img, (cx, cy), r, color, -1, cv2.LINE_AA)


def render_png(kind):
    kind = kind if kind in _PALETTE else "default"
    bg, fg = _PALETTE[kind]
    n = SIZE * _SCALE
    img = np.full((n, n, 3), bg, np.uint8)
    dark = tuple(int(c * 0.82) for c in fg)
    white = (252, 252, 252)
    cx, base = n // 2, int(n * 0.84)

    cv2.ellipse(img, (cx, base + 6), (int(n * 0.22), int(n * 0.025)), 0, 0, 360,
                tuple(int(c * 0.9) for c in bg), -1, cv2.LINE_AA)  # 그림자

    def s(v):  # 0~1 비율 → 픽셀
        return int(n * v)

    if kind == "cream":  # 넓은 단지
        _rrect(img, cx - s(.27), base - s(.30), cx + s(.27), base, s(.05), fg)
        _rrect(img, cx - s(.29), base - s(.43), cx + s(.29), base - s(.28), s(.04), dark)
        _rrect(img, cx - s(.17), base - s(.22), cx + s(.17), base - s(.08), s(.03), white)
    elif kind == "serum":  # 스포이드 병
        _rrect(img, cx - s(.17), base - s(.40), cx + s(.17), base, s(.05), fg)
        _rrect(img, cx - s(.07), base - s(.50), cx + s(.07), base - s(.38), s(.02), dark)
        cv2.ellipse(img, (cx, base - s(.57)), (s(.08), s(.10)), 0, 0, 360, dark, -1, cv2.LINE_AA)
        _rrect(img, cx - s(.11), base - s(.30), cx + s(.11), base - s(.12), s(.03), white)
    elif kind == "cleanser":  # 튜브
        pts = np.array([[cx - s(.20), base], [cx + s(.20), base], [cx + s(.14), base - s(.60)],
                        [cx - s(.14), base - s(.60)]], np.int32)
        cv2.fillPoly(img, [pts], fg, cv2.LINE_AA)
        _rrect(img, cx - s(.12), base - s(.70), cx + s(.12), base - s(.58), s(.02), dark)
        _rrect(img, cx - s(.12), base - s(.38), cx + s(.12), base - s(.16), s(.03), white)
    elif kind == "mist":  # 스프레이 병
        _rrect(img, cx - s(.15), base - s(.50), cx + s(.15), base, s(.05), fg)
        _rrect(img, cx - s(.06), base - s(.60), cx + s(.06), base - s(.48), s(.02), dark)
        _rrect(img, cx - s(.10), base - s(.68), cx + s(.14), base - s(.58), s(.03), dark)
        _rrect(img, cx - s(.10), base - s(.34), cx + s(.10), base - s(.14), s(.03), white)
    else:  # toner / default: 길쭉한 병
        _rrect(img, cx - s(.18), base - s(.50), cx + s(.18), base, s(.06), fg)
        _rrect(img, cx - s(.08), base - s(.60), cx + s(.08), base - s(.48), s(.02), dark)
        _rrect(img, cx - s(.11), base - s(.68), cx + s(.11), base - s(.58), s(.03), dark)
        _rrect(img, cx - s(.12), base - s(.36), cx + s(.12), base - s(.14), s(.03), white)

    img = cv2.resize(img, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()
