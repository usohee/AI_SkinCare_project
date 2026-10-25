"""피부 분석 알고리즘 검증 도구 (장비 실측 라벨 대비 오차율 백테스팅).

서버(main.py)와 무관한 오프라인 도구다. 알고리즘 본체는 app/services/skin_analyzer.py 에 있고,
여기서는 그 함수를 불러와 라벨(JSON/마스크)과 비교한다.

실행 (backend 폴더에서, 라벨 데이터가 있는 위치 기준 상대경로 사용):
    python tools/validate_algorithm.py
"""
import glob
import json
import os
import sys

import cv2
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.skin_analyzer import (  # noqa: E402
    MAX_VALUES, detect_acne, detect_pigmentation, detect_pore, detect_sebum,
    extract_roi, extract_roi_by_bbox, get_skin_type, normalize, preprocess,
)
import numpy as np  # noqa: E402

plt.rcParams["font.family"] = "Malgun Gothic"  # Windows 한글 폰트
plt.rcParams["axes.unicode_minus"] = False

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
                extract_roi(img_bgr)
            )
    else:
        roi_bgr_processed, roi_gray_calib = preprocess(
            extract_roi(img_bgr)
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
    roi_bgr_processed, _ = preprocess(img_bgr)   # ← extract_roi 제거
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


if __name__ == "__main__":

    # ── pigmentation / pore / sebum: 다중 샘플 검증 ──────
    skin_samples = [
        (r"pps\jpg_0001\sample.jpg", r"pps\labeling_0001"),
        (r"pps\jpg_0081\0081.jpg",   r"pps\labeling_0081"),
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