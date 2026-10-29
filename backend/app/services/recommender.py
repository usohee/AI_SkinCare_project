"""분석 점수에 따라 products 테이블에서 제품을 고른다. (성분표 기반의 단순 규칙)

- 감점이 큰 항목(30점 이상, 없으면 가장 큰 항목) 1~2개를 고른다.
- 항목마다 관련 성분 키워드가 전성분에 많이 들어 있는 제품을 고른다.
- 이 추천은 '전성분에 해당 성분이 포함됨'이라는 사실만 근거로 하며, 효능을 보장하지 않는다.
- products 테이블이 비어 있으면 기본 제품 3개로 대신한다.
"""
from .product_image import kind_for

THRESHOLD = 30
MAX_ITEMS = 3

# 항목 → (화면 표시 이름, [(전성분에서 찾을 글자, 화면에 보일 성분 이름), ...])
CONCERNS = {
    "acne": ("여드름", [("병풀", "병풀"), ("센텔라", "센텔라"), ("시카", "시카"), ("마데카", "마데카소사이드"),
                      ("살리실", "살리실산"), ("티트리", "티트리"), ("어성초", "어성초"), ("징크", "징크")]),
    "pore": ("모공", [("나이아신", "나이아신아마이드"), ("살리실", "살리실산"), ("베타인살리", "베타인살리실레이트"),
                    ("글루코노락톤", "글루코노락톤"), ("락토바이오닉", "락토바이오닉애씨드"), ("녹차", "녹차")]),
    "pigmentation": ("색소침착", [("나이아신", "나이아신아마이드"), ("아스코", "아스코빅애씨드"), ("알부틴", "알부틴"),
                              ("트라넥삼", "트라넥사믹애씨드"), ("비타민", "비타민")]),
    "sebum": ("피지", [("징크", "징크"), ("티트리", "티트리"), ("나이아신", "나이아신아마이드"),
                     ("살리실", "살리실산"), ("녹차", "녹차"), ("카올린", "카올린")]),
}
_ORDER = ("acne", "pigmentation", "pore", "sebum")

# products 테이블이 비어 있을 때 쓰는 기본 제품
FALLBACK = {
    "acne": {"name": "에이솔루션 아크네 클리어 세럼", "brand": "에이솔루션", "category": "세럼"},
    "sebum": {"name": "이니스프리 화산송이 모공 팩", "brand": "이니스프리", "category": "기초"},
    "default": {"name": "피지오겔 데일리 모이스처 크림", "brand": "피지오겔", "category": "크림"},
}


def pick_concerns(scores):
    """감점이 큰 순서로 최대 2개 항목."""
    ranked = sorted(_ORDER, key=lambda k: (-int(scores.get(k, 0)), _ORDER.index(k)))
    chosen = [k for k in ranked if int(scores.get(k, 0)) >= THRESHOLD][:2]
    return chosen or ranked[:1]


def _match(ingredients, keywords):
    """(찾은 키워드 수, 첫 등장 위치, 찾은 성분 이름들)"""
    text = str(ingredients or "").lower()
    found, first = [], len(text) + 1
    for needle, shown in keywords:
        pos = text.find(needle)
        if pos >= 0:
            if shown not in found:
                found.append(shown)
            first = min(first, pos)
    return len(found), first, found


def _from_db(db, concern, limit, used_ids):
    label, keywords = CONCERNS[concern]
    rows = db.execute(
        "SELECT product_id, product_name, brand, ingredients, category FROM products "
        "WHERE ingredients IS NOT NULL AND ingredients != ''"
    ).fetchall()
    scored = []
    for r in rows:
        if r["product_id"] in used_ids:
            continue
        hits, first, names = _match(r["ingredients"], keywords)
        if hits:
            scored.append((-hits, first, r["product_id"], r, names))
    scored.sort(key=lambda x: x[:3])
    out = []
    for _, _, pid, r, names in scored[:limit]:
        used_ids.add(pid)
        out.append({
            "product_id": pid,
            "name": r["product_name"],
            "brand": r["brand"] or "",
            "category": r["category"] or "",
            "reason": f"{label} 관련 · 전성분에 {', '.join(names[:3])} 포함",
            "image_path": f"/product-image/p{pid}",
        })
    return out


def _fallback(scores):
    top = pick_concerns(scores)
    items = [FALLBACK.get(k) for k in top if k in FALLBACK] or [FALLBACK["default"]]
    out = []
    for item in items + [FALLBACK["default"]]:
        if item["name"] in {o["name"] for o in out}:
            continue
        out.append({
            "product_id": None, "name": item["name"], "brand": item["brand"], "category": item["category"],
            "reason": "기본 추천", "image_path": f"/product-image/t-{kind_for(item['category'])}",
        })
    return out[:MAX_ITEMS]


def recommend(db, scores):
    concerns = pick_concerns(scores)
    used, result = set(), []
    for i, concern in enumerate(concerns):
        limit = (MAX_ITEMS - 1) if (i == 0 and len(concerns) > 1) else (MAX_ITEMS - len(result))
        result.extend(_from_db(db, concern, max(0, min(limit, MAX_ITEMS - len(result))), used))
    return result[:MAX_ITEMS] or _fallback(scores)


def with_image_urls(recs, base_url):
    """저장된 추천(상대 경로)에 현재 접속 주소를 붙여 앱이 바로 쓸 수 있는 image_url을 만든다."""
    base = base_url.rstrip("/")
    return [{**r, "image_url": base + r["image_path"]} for r in recs or [] if r.get("image_path")]
