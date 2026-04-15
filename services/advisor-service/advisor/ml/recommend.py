from collections import Counter, defaultdict
from datetime import timedelta

import requests
from django.conf import settings

from advisor.ml.behavior_v2 import infer_behavior_v2
from advisor.ml.ranker_v2 import build_popularity_counter, rank_products_v2
from advisor.models import UserEvent


SERVICE_ENDPOINTS = {
    "computer": (settings.COMPUTER_SERVICE_URL, "/api/computers/"),
    "mobile": (settings.MOBILE_SERVICE_URL, "/api/mobiles/"),
    "clothes": (settings.CLOTHES_SERVICE_URL, "/api/clothes/"),
    "tablet": (getattr(settings, "TABLET_SERVICE_URL", ""), "/api/tablets/"),
    "audio": (getattr(settings, "AUDIO_SERVICE_URL", ""), "/api/audios/"),
    "wearable": (
        getattr(settings, "WEARABLE_SERVICE_URL", ""),
        "/api/wearables/",
    ),
    "component": (
        getattr(settings, "COMPONENT_SERVICE_URL", ""),
        "/api/components/",
    ),
    "peripheral": (
        getattr(settings, "PERIPHERAL_SERVICE_URL", ""),
        "/api/peripherals/",
    ),
    "monitor": (getattr(settings, "MONITOR_SERVICE_URL", ""), "/api/monitors/"),
    "accessory": (
        getattr(settings, "ACCESSORY_SERVICE_URL", ""),
        "/api/accessories/",
    ),
    "charging": (
        getattr(settings, "CHARGING_SERVICE_URL", ""),
        "/api/chargings/",
    ),
    "book": (getattr(settings, "BOOK_SERVICE_URL", ""), "/api/books/"),
}

ALL_PRODUCT_TYPES = list(SERVICE_ENDPOINTS.keys())

CROSS_CATEGORY_RULES = {
    "computer": ["charging", "peripheral", "monitor", "component", "accessory"],
    "mobile": ["accessory", "charging", "audio", "wearable"],
    "tablet": ["accessory", "charging", "audio"],
    "audio": ["mobile", "accessory"],
    "wearable": ["mobile", "charging"],
    "component": ["computer", "peripheral", "monitor"],
    "peripheral": ["computer", "monitor", "component"],
    "monitor": ["computer", "component", "peripheral"],
    "accessory": ["mobile", "tablet", "computer"],
    "charging": ["mobile", "tablet", "wearable"],
    "book": ["computer", "mobile"],
    "clothes": ["accessory"],
}

MIN_CONFIDENCE_EXACT = 0.5
MIN_CONFIDENCE_TRENDING = 0.3

EVENT_SCORE = {
    "product_list_view": 1,
    "product_detail_view": 2,
    "search": 2,
    "add_to_cart": 4,
    "update_cart": 3,
    "remove_from_cart": -1,
    "checkout_start": 5,
    "order_created": 8,
    "review_created": 3,
    "chat_open": 1,
    "chat_message_sent": 2,
    "chat_recommendation_click": 3,
}


def _normalize_confidence(raw_score, default_score=0.5):
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = float(default_score)
    return round(max(0.0, min(1.0, score)), 4)


def _apply_confidence_threshold(items, min_confidence, default_score=0.5):
    filtered = []
    for item in items or []:
        confidence = _normalize_confidence(
            item.get("fusion_score", item.get("score")), default_score
        )
        item["confidence"] = confidence
        if confidence >= min_confidence:
            filtered.append(item)
    return filtered


def _normalize_product_types(product_types):
    if not product_types:
        return []
    if isinstance(product_types, str):
        product_types = [part.strip() for part in product_types.split(",") if part]

    result = []
    for item in product_types:
        value = str(item or "").strip().lower()
        if value in SERVICE_ENDPOINTS and value not in result:
            result.append(value)
    return result


def _expand_categories(base_categories):
    expanded = []
    for category in base_categories:
        if category in SERVICE_ENDPOINTS and category not in expanded:
            expanded.append(category)
        for related in CROSS_CATEGORY_RULES.get(category, []):
            if related in SERVICE_ENDPOINTS and related not in expanded:
                expanded.append(related)
    return expanded


def _is_in_stock(product):
    try:
        stock = float(product.get("stock", 0) or 0)
    except (TypeError, ValueError):
        stock = 0
    status = str(product.get("status") or "").strip().lower()
    return stock > 0 and status not in {"out_of_stock", "sold_out", "inactive"}


def _apply_diversity_limit(items, limit, ratio=0.3):
    if not items:
        return []

    max_per_category = max(1, int(limit * ratio))
    selected = []
    overflow = []
    counts = Counter()

    for item in items:
        category = item.get("product_type") or "unknown"
        if counts[category] < max_per_category:
            selected.append(item)
            counts[category] += 1
        else:
            overflow.append(item)
        if len(selected) >= limit:
            return selected[:limit]

    for item in overflow:
        if len(selected) >= limit:
            break
        selected.append(item)

    return selected[:limit]


def compute_diversity_stats(items):
    counts = Counter(item.get("product_type") or "unknown" for item in items or [])
    total = max(1, len(items or []))
    max_ratio = 0.0
    if counts:
        max_ratio = max(count / total for count in counts.values())
    return {
        "total": len(items or []),
        "by_category": dict(counts),
        "max_same_category_ratio": round(max_ratio, 4),
    }


def _annotate_reason(items, primary_categories):
    primary = primary_categories[0] if primary_categories else "san pham"
    for item in items:
        if item.get("reason"):
            continue
        item_type = item.get("product_type")
        if any(
            item_type in CROSS_CATEGORY_RULES.get(cat, []) for cat in primary_categories
        ):
            item["reason"] = f"Binh thuong duoc xem cung {primary}"
        elif item.get("trend_score", 0) > 0:
            item["reason"] = "Dang trending"
        else:
            item["reason"] = "Goi y dua tren hanh vi"


def fetch_products(product_type: str, limit: int = 12):
    config = SERVICE_ENDPOINTS.get(product_type)
    if not config:
        return []

    service_url, endpoint = config
    if not service_url:
        return []

    try:
        response = requests.get(f"{service_url}{endpoint}?page_size={limit}", timeout=8)
        if response.status_code != 200:
            return []
        payload = response.json()
        if isinstance(payload, dict):
            return payload.get("results", [])
        if isinstance(payload, list):
            return payload
    except requests.RequestException:
        return []
    return []


def summarize_behavior(user_id: str = "", session_id: str = ""):
    queryset = UserEvent.objects.exclude(metadata__seeded=True)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    elif session_id:
        queryset = queryset.filter(session_id=session_id)
    else:
        queryset = queryset.none()

    events = list(queryset.order_by("created_at"))
    counts = Counter(event.event_type for event in events)
    category_counter = Counter(
        event.product_type for event in events if event.product_type
    )
    product_counter = Counter(
        (event.product_type, event.product_id)
        for event in events
        if event.product_type and event.product_id
    )
    recent = events[-10:]
    buy_score = min(
        0.99,
        (
            category_counter.total()
            + sum(
                2
                for event in recent
                if event.event_type
                in {"add_to_cart", "checkout_start", "order_created"}
            )
        )
        / 20,
    )

    feature_payload = {
        "views": counts.get("product_detail_view", 0),
        "list_views": counts.get("product_list_view", 0),
        "searches": counts.get("search", 0),
        "cart_adds": counts.get("add_to_cart", 0),
        "cart_updates": counts.get("update_cart", 0),
        "checkouts": counts.get("checkout_start", 0),
        "orders": counts.get("order_created", 0),
        "reviews": counts.get("review_created", 0),
        "chat_messages": counts.get("chat_message_sent", 0),
        "buy_score_heuristic": sum(
            EVENT_SCORE.get(evt.event_type, 0) for evt in events
        ),
        "event_count": len(events),
        "top_category": (
            category_counter.most_common(1)[0][0] if category_counter else "computer"
        ),
    }
    behavior_profile = infer_behavior_v2(
        feature_payload, settings.ARTIFACTS_DIR, events=events
    )

    return {
        "buy_score": round(buy_score, 2),
        "top_categories": [category for category, _ in category_counter.most_common(3)],
        "recent_products": [
            {"product_type": product_type, "product_id": product_id}
            for (product_type, product_id), _ in product_counter.most_common(5)
        ],
        "event_count": len(events),
        "behavior_profile": behavior_profile,
    }


def get_trending_products(category: str, days: int = 7, limit: int = 3):
    if category not in SERVICE_ENDPOINTS:
        return []

    since = None
    if days > 0:
        from django.utils import timezone

        since = timezone.now() - timedelta(days=days)

    queryset = UserEvent.objects.filter(
        event_type="product_detail_view", product_type=category
    ).exclude(metadata__seeded=True)
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)

    counts = Counter(event.product_id for event in queryset if event.product_id)
    products = fetch_products(category, limit=max(limit * 4, 12))
    by_id = {item.get("id"): item for item in products}

    ranked = []
    for product_id, hits in counts.most_common():
        product = by_id.get(product_id)
        if not product or not _is_in_stock(product):
            continue
        product["product_type"] = category
        product["trend_score"] = round(min(1.0, (hits / 10.0) + 0.2), 4)
        product["reason"] = "Dang trending"
        ranked.append(product)
        if len(ranked) >= limit:
            return ranked

    if ranked:
        return ranked[:limit]

    fallback = []
    for product in products:
        if not _is_in_stock(product):
            continue
        product["product_type"] = category
        product["trend_score"] = 0.2
        product["reason"] = "Dang trending"
        fallback.append(product)
        if len(fallback) >= limit:
            break
    return fallback


def trending_products(limit: int = 6):
    counts = Counter(
        (event.product_type, event.product_id)
        for event in UserEvent.objects.filter(event_type="product_detail_view").exclude(
            metadata__seeded=True
        )
        if event.product_type and event.product_id
    )
    per_type = defaultdict(list)
    for (product_type, product_id), _ in counts.most_common():
        per_type[product_type].append(product_id)

    results = []
    for product_type in ALL_PRODUCT_TYPES:
        products = fetch_products(product_type, limit=limit)
        by_id = {product.get("id"): product for product in products}
        for product_id in per_type.get(product_type, []):
            if product_id in by_id:
                product = by_id[product_id]
                if not _is_in_stock(product):
                    continue
                product["product_type"] = product_type
                product["trend_score"] = 0.2
                product["reason"] = "Dang trending"
                results.append(product)
                if len(results) >= limit:
                    return results

    if results:
        return results[:limit]

    fallback = []
    for product_type in ALL_PRODUCT_TYPES:
        for product in fetch_products(product_type, limit=2):
            if not _is_in_stock(product):
                continue
            product["product_type"] = product_type
            product["trend_score"] = 0.2
            product["reason"] = "Dang trending"
            fallback.append(product)
    return fallback[:limit]


def recommend_products(
    user_id: str = "",
    session_id: str = "",
    limit: int = 6,
    ranker_variant: str = "auto",
    product_types=None,
):
    return recommend_products_v2(
        user_id=user_id,
        session_id=session_id,
        limit=limit,
        ranker_variant=ranker_variant,
        product_types=product_types,
    )


def _recommend_products_v1(summary, preferred_categories, recent_seen, limit: int):
    recommendations = []
    for product_type in preferred_categories:
        for product in fetch_products(product_type, limit=limit):
            key = (product_type, product.get("id"))
            if key in recent_seen:
                continue
            product["product_type"] = product_type
            product["reason"] = f"Based on your recent interest in {product_type}"
            recommendations.append(product)
            if len(recommendations) >= limit:
                return recommendations

    if not recommendations:
        return trending_products(limit=limit)
    return recommendations[:limit]


def _select_ranker_variant(ranker_variant: str, user_id: str, session_id: str):
    variant = (ranker_variant or "auto").strip().lower()
    if variant in {"v1", "v2"}:
        return variant

    if not getattr(settings, "RECOMMENDER_AB_ENABLED", False):
        default_variant = str(
            getattr(settings, "RECOMMENDER_DEFAULT_VARIANT", "v2")
        ).lower()
        return default_variant if default_variant in {"v1", "v2"} else "v2"

    identity = user_id or session_id or "anonymous"
    bucket = sum(ord(char) for char in identity) % 100
    # Sticky 50/50 split for A/B without external experiment framework.
    return "v2" if bucket >= 50 else "v1"


def recommend_products_v2(
    user_id: str = "",
    session_id: str = "",
    limit: int = 6,
    ranker_variant: str = "auto",
    product_types=None,
):
    summary = summarize_behavior(user_id=user_id, session_id=session_id)
    requested_types = _normalize_product_types(product_types)
    preferred_categories = (
        requested_types
        or summary["top_categories"]
        or [
            "computer",
            "mobile",
            "clothes",
        ]
    )
    expanded_categories = _expand_categories(preferred_categories) or ALL_PRODUCT_TYPES

    recent_seen = {
        (item["product_type"], item["product_id"])
        for item in summary["recent_products"]
        if item.get("product_type") and item.get("product_id")
    }

    variant = _select_ranker_variant(ranker_variant, user_id, session_id)
    if variant == "v1":
        items = _recommend_products_v1(summary, expanded_categories, recent_seen, limit)
        items = _apply_confidence_threshold(
            items, MIN_CONFIDENCE_EXACT, default_score=0.6
        )
        if not items:
            items = _apply_confidence_threshold(
                trending_products(limit=limit),
                MIN_CONFIDENCE_TRENDING,
                default_score=0.35,
            )
        items = _apply_diversity_limit(items, limit=limit)
        _annotate_reason(items, preferred_categories)
        summary["diversity_stats"] = compute_diversity_stats(items)
        summary["ranker"] = {"variant": "v1", "ab_bucket": "legacy"}
        return summary, items

    candidates = []
    for product_type in expanded_categories:
        for product in fetch_products(product_type, limit=limit * 2):
            key = (product_type, product.get("id"))
            if key in recent_seen:
                continue
            if not _is_in_stock(product):
                continue
            product["product_type"] = product_type
            candidates.append(product)

    if not candidates:
        fallback_items = []
        for category in preferred_categories[:3]:
            fallback_items.extend(get_trending_products(category, days=7, limit=3))
        if not fallback_items:
            fallback_items = trending_products(limit=limit)
        fallback_items = _apply_confidence_threshold(
            fallback_items,
            MIN_CONFIDENCE_TRENDING,
            default_score=0.35,
        )
        fallback_items = _apply_diversity_limit(fallback_items, limit=limit)
        _annotate_reason(fallback_items, preferred_categories)
        summary["diversity_stats"] = compute_diversity_stats(fallback_items)
        summary["ranker"] = {"variant": "v2", "ab_bucket": "fallback_trending"}
        return summary, fallback_items

    popularity_events = UserEvent.objects.filter(
        event_type="product_detail_view"
    ).exclude(metadata__seeded=True)
    popularity_counter = build_popularity_counter(popularity_events)
    ranked = rank_products_v2(candidates, summary, popularity_counter, limit=limit)

    ranked = _apply_confidence_threshold(
        ranked,
        MIN_CONFIDENCE_EXACT,
        default_score=0.6,
    )

    if not ranked:
        fallback_trending = []
        for category in preferred_categories[:3]:
            fallback_trending.extend(get_trending_products(category, days=7, limit=3))
        if not fallback_trending:
            fallback_trending = trending_products(limit=limit)
        ranked = _apply_confidence_threshold(
            fallback_trending,
            MIN_CONFIDENCE_TRENDING,
            default_score=0.35,
        )

    ranked = _apply_diversity_limit(ranked, limit=limit)
    _annotate_reason(ranked, preferred_categories)
    summary["diversity_stats"] = compute_diversity_stats(ranked)

    summary["ranker"] = {
        "variant": "v2",
        "ab_bucket": "fusion",
        "candidate_count": len(candidates),
        "min_confidence_exact": MIN_CONFIDENCE_EXACT,
        "min_confidence_trending": MIN_CONFIDENCE_TRENDING,
        "product_types": expanded_categories,
    }
    return summary, ranked[:limit]
