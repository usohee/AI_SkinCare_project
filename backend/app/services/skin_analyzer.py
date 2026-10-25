"""피부 분석 알고리즘 (OpenCV). 서버와 검증 도구(tools/validate_algorithm.py)가 함께 쓴다.

알고리즘 값(임계값, MAX_VALUES, 점수 공식)은 기존 backend/test.py와 동일하다.
여기에는 matplotlib/DB/Flask 의존성이 없다.
"""
import cv2
import numpy as np

# OpenCV 내장 얼굴 인식
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# 지표별 정규화 기준값 (이 값 이상이면 100점)
MAX_VALUES = {
    "acne": 50,
    "pigmentation": 250,
    "pore": 27.0,
    "sebum": 0.6,
}


# ── 1. 전처리 ────────────────────────────────────────────
def preprocess(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab = cv2.merge([clahe.apply(l), a, b])
    img_bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    img_gray = cv2.GaussianBlur(img_gray, (5, 5), 0)
    return img_bgr, img_gray


# ── 2. ROI 추출 ──────────────────────────────────────────
def extract_roi(img_bgr):
    """Haar Cascade 얼굴 크롭. 얼굴을 못 찾으면 이미지 중앙부를 사용한다."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        h, w = img_bgr.shape[:2]
        return img_bgr[h // 4:h * 3 // 4, w // 4:w * 3 // 4]
    x, y, w, h = faces[0]
    x1 = max(0, x - 20)
    y1 = max(0, y - 20)
    x2 = min(img_bgr.shape[1], x + w + 20)
    y2 = min(img_bgr.shape[0], y + h + 20)
    return img_bgr[y1:y2, x1:x2]


def extract_roi_by_bbox(img, bbox):
    x, y, w, h = bbox
    return img[y:y + h, x:x + w]


# ── 3. 탐지 알고리즘 ─────────────────────────────────────
def get_skin_type(roi_gray):
    """평균 밝기로 피부 타입 판별: 밝음 → oily, 어두움 → dry"""
    return "oily" if np.mean(roi_gray) >= 130 else "dry"


def detect_acne(roi_bgr):
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([165, 80, 80]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(mask1, mask2)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return len([c for c in contours if 500 < cv2.contourArea(c) < 3000])


def detect_pigmentation(roi_gray):
    min_area = 80 if get_skin_type(roi_gray) == "oily" else 100
    binary = cv2.adaptiveThreshold(
        roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, blockSize=51, C=20
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return len([c for c in contours if min_area < cv2.contourArea(c) < 1500])


def detect_pore(roi_gray):
    return float(cv2.Laplacian(roi_gray, cv2.CV_64F).var())


def detect_sebum(roi_gray):
    threshold = 200 if get_skin_type(roi_gray) == "oily" else 150
    _, thresh = cv2.threshold(roi_gray, threshold, 255, cv2.THRESH_BINARY)
    return float(np.count_nonzero(thresh)) / thresh.size


# ── 4. 정규화 / 점수 ─────────────────────────────────────
def normalize(key, value):
    return min(100, int(value / MAX_VALUES[key] * 100))


def compute_scores(raw):
    """지표별 감점 점수(낮을수록 양호)와 종합 점수(높을수록 양호)."""
    scores = {k: normalize(k, v) for k, v in raw.items()}
    total_score = max(0, 100 - round(sum(scores.values()) / len(scores)))
    return scores, total_score


def measure(roi_bgr_processed, roi_gray):
    return {
        "acne": detect_acne(roi_bgr_processed),
        "pigmentation": detect_pigmentation(roi_gray),
        "pore": detect_pore(roi_gray),
        "sebum": detect_sebum(roi_gray),
    }


# ── 5. 서버용 진입점 ─────────────────────────────────────
class ImageDecodeError(ValueError):
    pass


def decode_image(file_bytes):
    if not file_bytes:
        raise ImageDecodeError("빈 파일입니다.")
    img = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ImageDecodeError("이미지 디코딩 실패")
    return img


def analyze_image(img_bgr):
    """BGR 이미지 한 장 → 점수 묶음.

    반환: {"total_score", "scores", "raw_values"}  (raw_values는 DB 저장/리포트 입력용)
    """
    roi_bgr_processed, roi_gray = preprocess(extract_roi(img_bgr))
    raw = measure(roi_bgr_processed, roi_gray)
    scores, total_score = compute_scores(raw)
    raw_values = {
        "acne_count": raw["acne"],
        "pigmentation_count": raw["pigmentation"],
        "pore_variance": round(raw["pore"], 4),
        "sebum_ratio": round(raw["sebum"] * 100, 1),
    }
    return {"total_score": total_score, "scores": scores, "raw_values": raw_values}
