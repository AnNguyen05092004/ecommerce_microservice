from collections import Counter

# thuật toán chấm điểm và xếp hạng sản phẩm.
def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_status(value):
    return str(value or "").strip().lower()


def _is_in_stock(product):
    status = _normalize_status(product.get("status"))
    stock = _safe_float(product.get("stock"), default=1.0)
    if status in {"out_of_stock", "sold_out", "inactive", "archived"}:
        return False
    return stock > 0


def _behavior_affinity(product_type, summary):
    top_categories = summary.get("top_categories") or []
    profile = (summary.get("behavior_profile") or {}).get("label", "")
    confidence = _safe_float(
        (summary.get("behavior_profile") or {}).get("confidence"), 0
    )

    base = 0.35
    if product_type in top_categories[:1]:
        base += 0.45
    elif product_type in top_categories:
        base += 0.25

    # Lightweight profile-aware nudges.
    if profile == "impulse_buyer":
        base += 0.08
    elif profile == "researcher":
        base += 0.03
    elif profile == "window_shopper":
        base -= 0.04

    return min(1.0, max(0.0, base + confidence * 0.1))


def _price_score(product):
    # Simple normalization to avoid expensive outliers dominating recommendations.
    price = _safe_float(product.get("price"), 0)
    if price <= 0:
        return 0.5
    if price < 2_000_000:
        return 0.95
    if price < 10_000_000:
        return 0.8
    if price < 30_000_000:
        return 0.65
    return 0.45


def _diversity_penalty(candidate, picked):
    if not picked:
        return 0.0
    same_type = sum(
        1
        for item in picked
        if item.get("product_type") == candidate.get("product_type")
    )
    same_brand = sum(
        1
        for item in picked
        if item.get("brand") == candidate.get("brand") and item.get("brand")
    )
    return min(0.2, same_type * 0.04 + same_brand * 0.03)


def rank_products_v2(products, summary, popularity_counter, limit=6):
    """Rank products with fusion score and short explainability notes.

    Score = behavior_affinity + popularity + stock/status + price + diversity penalty.
    """
    scored = []
    max_popularity = max(popularity_counter.values(), default=1)

    for product in products:
        if not _is_in_stock(product):
            continue

        product_type = product.get("product_type") or "unknown"
        product_id = product.get("id") or product.get("product_id")
        pop_hits = popularity_counter.get((product_type, product_id), 0)
        popularity_score = pop_hits / max(1, max_popularity)
        affinity_score = _behavior_affinity(product_type, summary)
        price_score = _price_score(product)

        base_score = 0.55 * affinity_score + 0.3 * popularity_score + 0.15 * price_score
        scored.append(
            {
                "product": product,
                "base_score": base_score,
                "affinity_score": affinity_score,
                "popularity_score": popularity_score,
                "price_score": price_score,
                "popularity_hits": int(pop_hits),
            }
        )

    scored.sort(key=lambda row: row["base_score"], reverse=True)

    picked = []
    for row in scored:
        product = row["product"]
        penalty = _diversity_penalty(product, picked)
        fused = row["base_score"] - penalty
        product["fusion_score"] = round(float(fused), 4)
        product["reason_detail"] = {
            "affinity_score": round(float(row["affinity_score"]), 3),
            "popularity_score": round(float(row["popularity_score"]), 3),
            "price_score": round(float(row["price_score"]), 3),
            "diversity_penalty": round(float(penalty), 3),
            "popularity_hits": row["popularity_hits"],
        }

        reasons = []
        if row["affinity_score"] >= 0.65:
            reasons.append("Phu hop hanh vi gan day")
        if row["popularity_score"] >= 0.5:
            reasons.append("Dang duoc quan tam")
        if row["price_score"] >= 0.8:
            reasons.append("Muc gia hop ly")
        product["reason"] = ", ".join(reasons) or "Goi y tu ranker thong minh"

        picked.append(product)
        if len(picked) >= limit:
            break

    # Ensure deterministic output ordering by score desc for returned items.
    picked.sort(key=lambda item: item.get("fusion_score", 0), reverse=True)
    return picked[:limit]


def build_popularity_counter(events):
    return Counter(
        (event.product_type, event.product_id)
        for event in events
        if event.product_type and event.product_id
    )
