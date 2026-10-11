import cv2
import numpy as np
import matplotlib.pyplot as plt
import json
import sqlite3
import uuid
import os
import glob
from flask import Flask, request, jsonify
from matplotlib import rc
from werkzeug.security import generate_password_hash, check_password_hash
from llm_service import generate_report
import matplotlib.font_manager as fm
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

app = Flask(__name__)
app.json.ensure_ascii = False

# ── DB 초기화 (백엔드/DB) ─────────────────────────
DB_PATH = "skincare.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email VARCHAR UNIQUE,
            password_hash VARCHAR,
            nickname VARCHAR,
            gender VARCHAR,
            birth_year INTEGER,
            skin_type VARCHAR,
            skin_concern TEXT,
            allergy_ingredients TEXT,
            preferred_formulations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skin_analyses (
            analyses_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            image_url VARCHAR,
            score_total INTEGER,
            score_acne INTEGER,
            score_pore INTEGER,
            score_pigmentation INTEGER,
            score_sebum INTEGER,
            raw_values TEXT,
            bbox_coordinates TEXT,
            llm_report TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# OpenCV 내장 얼굴 인식 (mediapipe 대체)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

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
def extract_roi_mediapipe(img_bgr):
    """OpenCV Haar Cascade 기반 얼굴 크롭"""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        h, w = img_bgr.shape[:2]
        return img_bgr[h//4:h*3//4, w//4:w*3//4]
    x, y, w, h = faces[0]
    x1 = max(0, x - 20)
    y1 = max(0, y - 20)
    x2 = min(img_bgr.shape[1], x + w + 20)
    y2 = min(img_bgr.shape[0], y + h + 20)
    return img_bgr[y1:y2, x1:x2]

def extract_roi_by_bbox(img, bbox):
    x, y, w, h = bbox
    return img[y:y+h, x:x+w]

# ── 3. 탐지 알고리즘 ─────────────────────────────────────
def get_skin_type(roi_gray):
    """
    평균 밝기로 피부 타입 자동 판별
    밝음(지성/보통) vs 어두움(건성/색소침착)
    """
    mean_brightness = np.mean(roi_gray)
    if mean_brightness >= 130:
        return "oily"    # 지성 (밝은 피부)
    else:
        return "dry"     # 건성 (어두운 피부)

def detect_acne(roi_bgr):
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0,  80, 80]),  np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([165, 80, 80]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(mask1, mask2)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))  # 3→7 (노이즈 제거 강화)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return len([c for c in contours if 500 < cv2.contourArea(c) < 3000])
    #                                   ↑ 10→200         800→3000
def detect_pigmentation(roi_gray):
    skin_type = get_skin_type(roi_gray)
    if skin_type == "oily":
        min_area = 80    # 지성 → 작은 반점도 감지
    else:
        min_area = 100   # 건성/중년 → 주름 노이즈 제거
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
    skin_type = get_skin_type(roi_gray)
    if skin_type == "oily":
        threshold = 200   # 지성 → 높은 임계값 (반사 많음)
    else:
        threshold = 150   # 건성 → 낮은 임계값 (반사 적음)
    _, thresh = cv2.threshold(roi_gray, threshold, 255, cv2.THRESH_BINARY)
    return float(np.count_nonzero(thresh)) / thresh.size

# ── 4. 정규화 ────────────────────────────────────────────
MAX_VALUES = {
    "acne":         50,
    "pigmentation": 250,
    "pore":         27.0,
    "sebum":        0.6,
}

def normalize(key, value):
    return min(100, int(value / MAX_VALUES[key] * 100))

# ── 5. 라벨 파싱 ─────────────────────────────────────────
def parse_label_files(json_paths):
    ref = {"pigmentation_count": None, "pore_avg": None,
           "moisture_avg": None, "bbox_by_part": {}}
    moisture_vals, pore_vals = [], []

    for path in json_paths:
        if not os.path.exists(path): continue
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        part = d["images"]["facepart"]
        ref["bbox_by_part"][part] = d["images"]["bbox"]
        eq = d.get("equipment") or {}
        if part == 0:
            ref["pigmentation_count"] = eq.get("pigmentation_count")
        if part == 1 and "forehead_moisture" in eq:
            moisture_vals.append(eq["forehead_moisture"])
        if part == 5:
            if "l_cheek_pore"     in eq: pore_vals.append(eq["l_cheek_pore"])
            if "l_cheek_moisture" in eq: moisture_vals.append(eq["l_cheek_moisture"])
        if part == 6:
            if "r_cheek_pore"     in eq: pore_vals.append(eq["r_cheek_pore"])
            if "r_cheek_moisture" in eq: moisture_vals.append(eq["r_cheek_moisture"])

    if pore_vals:     ref["pore_avg"]     = round(sum(pore_vals)     / len(pore_vals),     1)
    if moisture_vals: ref["moisture_avg"] = round(sum(moisture_vals) / len(moisture_vals), 1)
    return ref

# ── 6. 오차 계산 ─────────────────────────────────────────
def calc_error(label, algo, label_max, key):
    if label is None or algo is None: return None
    error = abs(algo - label)
    rate  = round(error / max(label, 1) * 100, 1)
    ratio = algo / max(label, 1)
    if ratio > 1.3:
        hint = f"  ▲ 과검출 → MAX_VALUES['{key}'] 를 {round(MAX_VALUES[key]*ratio,1)} 으로 올려봐"
    elif ratio < 0.7:
        hint = f"  ▼ 미검출 → MAX_VALUES['{key}'] 를 {round(MAX_VALUES[key]*ratio,1)} 으로 내려봐"
    else:
        hint = f"  ✓ 오차 {rate}% — 허용 범위 (30% 이내)"
    return {"error": error, "rate": rate, "hint": hint}

# ── 7. 비교 출력 ─────────────────────────────────────────
def compare(ref, my_raw, my_scores):
    moisture_as_sebum = round(100 - ref["moisture_avg"], 1) if ref["moisture_avg"] else None
    print("\n" + "="*52)
    print("      [오차율 백테스팅] 알고리즘 vs 전문 장비 실측 비교")
    print("="*52)
    print(f"  {'항목':<16} {'장비 측정치':>12}  {'내 알고리즘':>12}  {'오차율':>6}")
    print("-"*52)
    errors = {}

    pig_err = calc_error(ref["pigmentation_count"], my_raw["pigmentation"], MAX_VALUES["pigmentation"], "pigmentation")
    if pig_err:
        print(f"  {'pigmentation':<16} {ref['pigmentation_count']:>12}개  {int(my_raw['pigmentation']):>11}개  {pig_err['rate']:>5}%")
        print(pig_err["hint"])
        errors["pigmentation"] = pig_err["rate"]

    pore_score_label = min(100, int(ref["pore_avg"] / 1000 * 100)) if ref["pore_avg"] else None
    pore_err = calc_error(pore_score_label, my_scores["pore"], 100, "pore")
    if pore_err:
        print(f"  {'pore(점수)':<16} {pore_score_label:>11}점  {my_scores['pore']:>11}점  {pore_err['rate']:>5}%")
        print(pore_err["hint"])
        errors["pore"] = pore_err["rate"]

    if moisture_as_sebum is not None:
        sebum_algo = round(my_raw["sebum"] * 100, 1)
        sebum_err  = calc_error(moisture_as_sebum, sebum_algo, 100, "sebum")
        if sebum_err:
            print(f"  {'sebum(수분역)':<16} {moisture_as_sebum:>11}%  {sebum_algo:>11}%  {sebum_err['rate']:>5}%")
            print(sebum_err["hint"])
            errors["sebum"] = sebum_err["rate"]

    print("="*52)
    return errors

# ── 8. 시각화 ────────────────────────────────────────────
def visualize(my_scores, ref, errors, save_path="result.png"):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    ax1 = axes[0]
    keys, values = list(my_scores.keys()), list(my_scores.values())
    bars = ax1.bar(keys, values, color=["#faf1f2", "#f1d1d2", "#c1a3a3", "#7d5959"])
    ax1.set_ylim(0, 100)
    ax1.set_title("내 알고리즘 지표별 감점 점수 (낮을수록 우수)")
    ax1.set_ylabel("점수 (Scale 0-100)")
    for bar, v in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width()/2, v + 1.5, str(v), ha='center', fontsize=10)

    ax2 = axes[1]
    if errors:
        err_keys, err_vals = list(errors.keys()), list(errors.values())
        bar_colors = ["#86dadb" if v <= 30 else "#007095" for v in err_vals]
        bars2 = ax2.bar(err_keys, err_vals, color=bar_colors)
        ax2.axhline(y=30, color='red', linestyle='--', linewidth=1, label='캡스톤 수용 목표치 (30%)')
        ax2.set_ylim(0, max(max(err_vals) * 1.3, 50))
        ax2.set_title("의료 진단 장비 실측치 대비 편차 오차율 (%)")
        ax2.set_ylabel("오차율 (%)")
        ax2.legend()
        for bar, v in zip(bars2, err_vals):
            ax2.text(bar.get_x() + bar.get_width()/2, v + 0.5, f"{v}%", ha='center', fontsize=10)
    else:
        ax2.text(0.5, 0.5, "비교용 라벨 JSON 없음", ha='center', va='center',
                 transform=ax2.transAxes, color='gray')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"  [시각화 완성] 결과 저장: {save_path}")

# ── 9. 메인 파이프라인 ───────────────────────────────────
def analyze_pipeline(image_path, json_paths=None):
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"이미지 없음: {image_path}")

    ref = None
    if json_paths:
        ref = parse_label_files(json_paths)
        bbox_full = ref["bbox_by_part"].get(0)
        if bbox_full:
            roi_bgr_processed, roi_gray_calib = preprocess(
                extract_roi_by_bbox(img_bgr, bbox_full)
            )
        else:
            roi_bgr_processed, roi_gray_calib = preprocess(
                extract_roi_mediapipe(img_bgr)
            )
    else:
        roi_bgr_processed, roi_gray_calib = preprocess(
            extract_roi_mediapipe(img_bgr)
        )

    raw = {
        "acne":         detect_acne(roi_bgr_processed),
        "pigmentation": detect_pigmentation(roi_gray_calib),
        "pore":         detect_pore(roi_gray_calib),
        "sebum":        detect_sebum(roi_gray_calib),
    }
    print(f"  [피부 타입 판별] {get_skin_type(roi_gray_calib)} (평균 밝기: {np.mean(roi_gray_calib):.1f})")
    scores = {k: normalize(k, v) for k, v in raw.items()}
    total_score = max(0, 100 - round(sum(scores.values()) / len(scores)))

    print("\n" + "═"*30 + "\n  [로컬 수동 테스트 검증 결과]\n" + "═"*30)
    for k, v in scores.items():
        if k in ["acne", "pigmentation"]:
            print(f"  {k:>14}: {v:>3}점  (Raw 수치: {int(raw[k])}개)")
        else:
            print(f"  {k:>14}: {v:>3}점  (Raw 수치: {raw[k]:.4f})")
    print(f"  {'종합 피부 점수':>12}: {total_score}점")

    errors = compare(ref, raw, scores) if ref else {}
    visualize(scores, ref or {}, errors)
    return scores, total_score, errors

# ── acne 전용 파이프라인 ─────────────────────────────────
def parse_acne_mask(mask_path):
    """
    ACNE04 gt_mask PNG → 여드름 개수 + contour 추출
    흰색 픽셀(255) = 여드름 영역
    """
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None

    _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 노이즈 제거: 너무 작은 건 제외
    spots = [c for c in contours if cv2.contourArea(c) > 10]

    return {
        "total":    len(spots),
        "contours": spots,
        "mask":     binary
    }


def analyze_acne_pipeline(image_path, mask_path):
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        print(f"이미지 없음: {image_path}")
        return

    # clean_roi는 이미 배경 제거됨 → ROI 크롭 생략
    roi_bgr_processed, _ = preprocess(img_bgr)   # ← extract_roi_mediapipe 제거
    my_count = detect_acne(roi_bgr_processed)
    # ... 이하 동일

    label = parse_acne_mask(mask_path)

    print(f"\n  내 알고리즘 acne 개수: {my_count}개")

    if label:
        real  = label["total"]
        error = abs(my_count - real)
        rate  = round(error / max(real, 1) * 100, 1)

        print(f"  ACNE04 마스크 개수:    {real}개")
        print(f"  오차율:                {rate}%")

        if rate <= 30:
            print("  ✓ 허용 범위 이내")
        elif my_count > real:
            print("  ▲ 과검출 → 면적 하한 올려봐 (50 → 80)")
        else:
            print("  ▼ 미검출 → 면적 하한 내려봐 (50 → 20)")

        # 시각화: 마스크 오버레이 + 개수 비교
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # 원본 이미지
        axes[0].imshow(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        axes[0].set_title("원본 이미지")
        axes[0].axis('off')

        # ACNE04 마스크
        axes[1].imshow(label["mask"], cmap='Reds')
        axes[1].set_title(f"ACNE04 정답 마스크 ({real}개)")
        axes[1].axis('off')

        # 개수 비교
        axes[2].bar(["ACNE04 (정답)", "내 알고리즘"],
                    [real, my_count],
                    color=["#b9e49a", "#E74C3C" if rate > 30 else "#76a3cb"])
        axes[2].set_title(f"acne 개수 비교 (오차율: {rate}%)")
        axes[2].set_ylabel("개수")
        for i, v in enumerate([real, my_count]):
            axes[2].text(i, v + 0.1, str(v), ha='center', fontsize=12)

        plt.tight_layout()
        plt.savefig("acne_result.png", dpi=150)
        plt.show()
        print("  acne 결과 저장: acne_result.png")
        return rate
    return None

# ── 10. Flask API ────────────────────────────────────────
@app.route('/analyze-skin', methods=['POST'])
def analyze_skin_api():
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "이미지 없음"}), 400
    file = request.files['image']
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return jsonify({"success": False, "message": "이미지 디코딩 실패"}), 400

    roi_bgr_processed, roi_gray = preprocess(extract_roi_mediapipe(img_bgr))
    raw = {
        "acne":         detect_acne(roi_bgr_processed),
        "pigmentation": detect_pigmentation(roi_gray),
        "pore":         detect_pore(roi_gray),
        "sebum":        detect_sebum(roi_gray),
    }
    scores = {k: normalize(k, v) for k, v in raw.items()}
    total_score = max(0, 100 - round(sum(scores.values()) / len(scores)))

    raw_values = {
        "acne_count":         raw["acne"],
        "pigmentation_count": raw["pigmentation"],
        "pore_variance":      round(raw["pore"], 4),
        "sebum_ratio":        round(raw["sebum"] * 100, 1)
    }

    # [LLM 연동] 수치 -> 자연어 리포트 생성
    analysis_data = {
        "success": True,
        "total_score": total_score,
        "scores": scores,
        "raw_values": raw_values,
    }
    llm_result = generate_report(analysis_data)

    # 백엔드/DB - 분석 결과 즉시 DB에 저장
    user_id = request.form.get("user_id") or str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO skin_analyses
        (user_id, score_total, score_acne, score_pore, score_pigmentation, score_sebum, raw_values, llm_report)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, total_score,
            scores.get("acne"), scores.get("pore"),
            scores.get("pigmentation"), scores.get("sebum"),
            json.dumps(raw_values),
            json.dumps(llm_result, ensure_ascii=False)
        ))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "user_id": user_id,
        "total_score": total_score,
        "scores": scores,
        "raw_values": raw_values,
        "llm_report": llm_result["report"],
        "llm_metadata": llm_result["metadata"],
        "llm_error": llm_result["error"]
    }), 200

# ── 11. 히스토리 저장/조회 API (백엔드/DB) ────────────────
@app.route('/history/<user_id>', methods=['GET'])
def get_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT analyses_id, score_total, score_acne, score_pore,
                score_pigmentation, score_sebum, raw_values, llm_report, created_at
            FROM skin_analyses
            WHERE user_id = ?
            ORDER BY created_at ASC
        """, (user_id,)).fetchall()
    conn.close()

    history = [dict(row) for row in rows]
    for h in history:
        h["raw_values"] = json.loads(h["raw_values"]) if h["raw_values"] else {}

        stored = json.loads(h["llm_report"]) if h["llm_report"] else None
        if stored:
            h["llm_report"] = stored.get("report")       # 리포트 본문만
            h["llm_metadata"] = stored.get("metadata")   # 출처, fallback 여부 등
        else:
            h["llm_report"] = None
            h["llm_metadata"] = None

    return jsonify({"success": True, "user_id": user_id, "history": history}), 200

# ── 12. 회원가입 / 로그인 API (백엔드/DB) ─────────────────
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    nickname = data.get("nickname", "")

    if not email or not password:
        return jsonify({"success": False, "message": "이메일/비밀번호 필요"}), 400

    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "message": "이미 가입된 이메일,"}), 409

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    conn.execute("""
        INSERT INTO users 
        (user_id, email, password_hash, nickname)
        VALUES (?, ?, ?, ?)
    """, (user_id, email, password_hash, nickname))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "user_id": user_id}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "이메일 또는 비밀번호가 틀렸습니다."}), 401

    return jsonify({"success": True, "user_id": user["user_id"], "nickname": user['nickname']}), 200

# ── 13. 프로필 수정 API (백엔드/DB) ─────────────────────────────────────
@app.route('/users/<user_id>/profile', methods=['PUT'])
def update_profile(user_id):
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"success": False, "message": "존재하지 않는 사용자"}), 404

    conn.execute("""
        UPDATE users
        SET gender = ?,
            birth_year = ?,
            skin_type = ?,
            skin_concern = ?,
            allergy_ingredients = ?,
            preferred_formulations = ?
        WHERE user_id = ?
    """, (
        data.get("gender"),
        data.get("birth_year"),
        data.get("skin_type"),
        json.dumps(data.get("skin_concern", [])),
        json.dumps(data.get("allergy_ingredients", [])),
        json.dumps(data.get("preferred_formulations", [])),
        user_id
    ))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "user_id": user_id}), 200


@app.route('/users/<user_id>/profile', methods=['GET'])
def get_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    if user is None:
        return jsonify({"success": False, "message": "존재하지 않는 사용자"}), 404

    profile = dict(user)
    profile.pop("password_hash", None)  # 비밀번호 해시는 응답에 절대 포함하지 않음
    for field in ["skin_concern", "allergy_ingredients", "preferred_formulations"]:
        profile[field] = json.loads(profile[field]) if profile[field] else []

    return jsonify({"success": True, "profile": profile}), 200

# ── 14. 엔트리포인트 ─────────────────────────────────────
if __name__ == "__main__":

    # ── pigmentation / pore / sebum: 다중 샘플 검증 ──────
    skin_samples = [
        (r"pps\jpg_0001\sample.jpg", "pps\labeling_0001"),
        (r"pps\jpg_0081\0081.jpg",   "pps\labeling_0081"),
    ]

    all_errors = {"pigmentation": [], "pore": [], "sebum": []}

    for img_path, label_dir in skin_samples:
        if not os.path.exists(img_path):
            print(f"  ⚠ 건너뜀: {img_path}")
            continue
        json_paths = sorted(glob.glob(os.path.join(label_dir, "*.json")))
        print(f"\n{'★'*40}")
        print(f"  [피부 검증] {img_path}")
        print(f"{'★'*40}")
        scores, total, errors = analyze_pipeline(img_path, json_paths)
        for key, val in errors.items():
            if key in all_errors:
                all_errors[key].append(val)

    # 평균 오차율 출력
    print("\n" + "="*52)
    print("  [전체 샘플 평균 오차율]")
    print("="*52)
    for key, vals in all_errors.items():
        if vals:
            avg = round(sum(vals) / len(vals), 1)
            status = "✅" if avg <= 30 else "❌"
            print(f"  {key:>14}: 평균 {avg}%  {status}")

    # ── acne: 다중 샘플 검증 ─────────────────────────────
    acne_samples = [
        (r"acne\img_data\levle2_81.jpg",  r"acne\gt_mask\levle2_81.png"),
        (r"acne\img_data\levle3_94.jpg",  r"acne\gt_mask\levle3_94.png"),
    ]

    acne_errors = []

    for img_path, mask_path in acne_samples:
        if not os.path.exists(img_path):
            print(f"  ⚠ 건너뜀: {img_path}")
            continue
        print(f"\n{'★'*40}")
        print(f"  [acne 검증] {img_path}")
        print(f"{'★'*40}")
        result = analyze_acne_pipeline(img_path, mask_path)
        if result is not None:
            acne_errors.append(result)

    if acne_errors:
        avg_acne = round(sum(acne_errors) / len(acne_errors), 1)
        status = "✅" if avg_acne <= 30 else "❌"
        print(f"\n  {'acne':>14}: 평균 {avg_acne}%  {status}")

    app.run(host='0.0.0.0', port=5000, debug=True)