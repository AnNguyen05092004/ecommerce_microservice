import json
import logging
import re
import time
from collections import Counter, deque
from pathlib import Path
from types import SimpleNamespace
import unicodedata

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .logging_config import LogContext, setup_logging, get_request_id
from .ml.kb import get_retrieval_mode, retrieve_documents
from .ml.kb_graph import retrieve_products_graph
from .ml.metrics import get_metrics
from .ml.model_selection_report import PRODUCTION_MODEL_MANIFEST
from .ml.recommend import (
    SERVICE_ENDPOINTS,
    fetch_products,
    recommend_products,
    summarize_behavior,
    trending_products,
)
from .models import UserEvent
from .serializers import (
    ChatRequestSerializer,
    KeywordSuggestionRequestSerializer,
    RecommendationRequestSerializer,
    SemanticSearchRequestSerializer,
    TrackEventSerializer,
)


logger = setup_logging("advisor")
metrics = get_metrics()

CACHE_TTL_SECONDS = 45
METRIC_HISTORY_LIMIT = 500
CB_FAILURE_THRESHOLD = 3
CB_COOLDOWN_SECONDS = 45

CB_STATE = {
    "consecutive_failures": 0,
    "open_until": 0.0,
    "last_error": "",
    "last_provider_status": 0,
    "last_provider_message": "",
}
CHAT_METRICS = deque(maxlen=METRIC_HISTORY_LIMIT)

PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore\s+previous\s+instructions",
        r"bypass\s+safety",
        r"system\s+prompt",
        r"developer\s+message",
        r"jailbreak",
        r"reveal\s+prompt",
    ]
]

TOXIC_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bkill\b",
        r"\bhate\b",
        r"\bterror\b",
        r"\bsuicide\b",
        r"\bbomb\b",
    ]
]

GROUNDING_STOPWORDS = {
    "toi",
    "khong",
    "va",
    "la",
    "cho",
    "trong",
    "cua",
    "nhung",
    "this",
    "that",
    "with",
    "from",
    "you",
    "your",
    "have",
    "will",
}


SEED_KEYWORDS = {
    "computer": [
        "laptop gaming",
        "laptop văn phòng",
        "laptop sinh viên",
        "ultrabook mỏng nhẹ",
        "macbook pro",
        "laptop đồ họa",
    ],
    "mobile": [
        "điện thoại chụp ảnh đẹp",
        "điện thoại pin trâu",
        "điện thoại chơi game",
        "iphone giá tốt",
        "android flagship",
        "điện thoại dưới 10 triệu",
    ],
    "clothes": [
        "áo thun basic",
        "áo khoác nam",
        "quần jean nữ",
        "áo sơ mi công sở",
        "thời trang mùa hè",
        "đồ thể thao nữ",
    ],
    "all": [
        "laptop cho học tập",
        "điện thoại chơi game",
        "quần áo basic",
        "sản phẩm bán chạy",
        "khuyến mãi hôm nay",
    ],
}

SUPPORTED_PRODUCT_TYPES = list(SERVICE_ENDPOINTS.keys())
SUPPORTED_PRODUCT_TYPE_SET = set(SUPPORTED_PRODUCT_TYPES)


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D").lower().strip()


def _estimate_tokens(text: str):
    return max(1, len((text or "").split()))


def _is_circuit_open():
    return time.time() < CB_STATE["open_until"]


def _register_cloud_success():
    CB_STATE["consecutive_failures"] = 0
    CB_STATE["last_error"] = ""
    CB_STATE["last_provider_status"] = 200
    CB_STATE["last_provider_message"] = "ok"


def _register_cloud_failure(reason: str, status_code: int = 0, message: str = ""):
    CB_STATE["consecutive_failures"] += 1
    CB_STATE["last_error"] = reason
    CB_STATE["last_provider_status"] = int(status_code or 0)
    CB_STATE["last_provider_message"] = (message or "")[:300]
    if CB_STATE["consecutive_failures"] >= CB_FAILURE_THRESHOLD:
        CB_STATE["open_until"] = time.time() + CB_COOLDOWN_SECONDS


def _guardrail_check(message: str):
    text = message or ""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return True, "prompt_injection_pattern"
    for pattern in TOXIC_PATTERNS:
        if pattern.search(text):
            return True, "sensitive_or_toxic_request"
    return False, ""


def _is_trending_intent(message: str):
    normalized = _normalize_text(message or "")
    keywords = [
        "khuyen mai",
        "promotion",
        "giam gia",
        "hot",
        "trending",
        "ban chay",
        "best seller",
    ]
    return any(keyword in normalized for keyword in keywords)


def _cache_key(message: str, language: str, product_type: str, product_id):
    normalized = _normalize_text(message)
    return f"advisor:chat:{language}:{product_type}:{product_id}:{normalized}"


def _extract_keywords(text: str, limit: int = 8):
    normalized = _normalize_text(text or "")
    tokens = re.findall(r"[a-z0-9]{3,}", normalized)
    keywords = []
    seen = set()
    for token in tokens:
        if token in GROUNDING_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _is_answer_grounded(answer: str, documents):
    if not answer or not documents:
        return False

    corpus_parts = []
    for doc in documents:
        corpus_parts.append(getattr(doc, "title", "") or "")
        corpus_parts.append(getattr(doc, "content", "") or "")
        corpus_parts.append(getattr(doc, "category", "") or "")
    corpus = _normalize_text(" ".join(corpus_parts))
    if not corpus:
        return False

    keywords = _extract_keywords(answer)
    if not keywords:
        return True

    matched = sum(1 for kw in keywords if kw in corpus)
    required = 1 if len(keywords) < 4 else 2
    return matched >= required


def _build_source_attribution(documents):
    if not documents:
        return {"text": "", "title": "", "source": ""}

    doc = documents[0]
    title = getattr(doc, "title", "") or "Tai lieu tham khao"
    source = getattr(doc, "source", "") or ""
    text = f"Thong tin tham khao: {title}"

    return {"text": text, "title": title, "source": source}


def _record_chat_metric(payload: dict):
    enriched = dict(payload)
    enriched.setdefault("timestamp", time.time())
    enriched.setdefault("operation", "chat")
    CHAT_METRICS.append(enriched)


def _metrics_snapshot():
    history = list(CHAT_METRICS)
    if not history:
        return {
            "window": 0,
            "fallback_rate": 0.0,
            "cache_hit_rate": 0.0,
            "avg_total_ms": 0.0,
            "avg_retrieval_ms": 0.0,
            "avg_generation_ms": 0.0,
            "error_rate": 0.0,
        }

    size = len(history)
    fallback = sum(1 for row in history if row.get("status") == "fallback")
    cache_hits = sum(1 for row in history if row.get("cache_hit"))
    errors = sum(1 for row in history if row.get("status") in {"blocked", "error"})
    return {
        "window": size,
        "fallback_rate": round(fallback / size, 4),
        "cache_hit_rate": round(cache_hits / size, 4),
        "avg_total_ms": round(sum(row.get("total_ms", 0) for row in history) / size, 2),
        "avg_retrieval_ms": round(
            sum(row.get("retrieval_ms", 0) for row in history) / size, 2
        ),
        "avg_generation_ms": round(
            sum(row.get("generation_ms", 0) for row in history) / size, 2
        ),
        "error_rate": round(errors / size, 4),
    }


def _chat_completion(prompt: str):
    provider = str(getattr(settings, "LLM_PROVIDER", "openai")).strip().lower()
    if provider == "gemini":
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        if not api_key:
            return "", False, "missing_api_key", 0, "GEMINI_API_KEY is empty"

        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "You are an e-commerce advisor. Answer only from the provided context. If context is missing, say so clearly.\n\n"
                                    + prompt
                                }
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.3},
                },
                timeout=25,
            )
            if response.status_code != 200:
                detail = ""
                reason = "provider_error"
                try:
                    payload = response.json()
                    err = payload.get("error", {}) if isinstance(payload, dict) else {}
                    status_text = str(err.get("status") or "").strip().upper()
                    detail = str(err.get("message") or "")
                    if response.status_code in {401, 403}:
                        reason = "provider_unauthorized"
                    elif response.status_code == 429:
                        reason = "provider_rate_limited_or_quota"
                    elif "RESOURCE_EXHAUSTED" in status_text:
                        reason = "provider_insufficient_quota"
                    elif "model" in detail.lower() and "not" in detail.lower():
                        reason = "provider_model_unavailable"
                except ValueError:
                    detail = response.text[:300]
                logger.warning(
                    "Gemini request failed status=%s reason=%s detail=%s",
                    response.status_code,
                    reason,
                    (detail or "")[:180],
                )
                return "", False, reason, int(response.status_code), detail

            payload = response.json()
            candidates = (
                payload.get("candidates") if isinstance(payload, dict) else None
            )
            if not candidates:
                return (
                    "",
                    False,
                    "provider_empty_response",
                    200,
                    "No candidates returned",
                )

            parts = (
                candidates[0].get("content", {}).get("parts", [])
                if isinstance(candidates[0], dict)
                else []
            )
            content = "\n".join(
                str(part.get("text", "")) for part in parts if isinstance(part, dict)
            ).strip()
            if not content:
                return "", False, "provider_empty_response", 200, "Empty text content"
            return content, True, "ok", 200, ""
        except (requests.RequestException, KeyError, IndexError, ValueError):
            return (
                "",
                False,
                "provider_network_or_parse_error",
                0,
                "request/parse exception",
            )

    if not settings.OPENAI_API_KEY:
        return "", False, "missing_api_key", 0, "OPENAI_API_KEY is empty"

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_CHAT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an e-commerce advisor. Answer only from the provided context. If context is missing, say so clearly.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
            timeout=25,
        )
        if response.status_code != 200:
            detail = ""
            reason = "provider_error"
            try:
                payload = response.json()
                err = payload.get("error", {}) if isinstance(payload, dict) else {}
                err_type = str(err.get("type") or "").strip().lower()
                err_code = str(err.get("code") or "").strip().lower()
                detail = str(err.get("message") or "")
                if response.status_code == 401:
                    reason = "provider_unauthorized"
                elif response.status_code == 429:
                    reason = "provider_rate_limited_or_quota"
                elif "insufficient_quota" in {err_type, err_code}:
                    reason = "provider_insufficient_quota"
                elif "model" in detail.lower() and "not" in detail.lower():
                    reason = "provider_model_unavailable"
            except ValueError:
                detail = response.text[:300]
            logger.warning(
                "OpenAI request failed status=%s reason=%s detail=%s",
                response.status_code,
                reason,
                (detail or "")[:180],
            )
            return "", False, reason, int(response.status_code), detail
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return content, True, "ok", 200, ""
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return (
            "",
            False,
            "provider_network_or_parse_error",
            0,
            "request/parse exception",
        )


def _prepare_context_documents(documents, max_chars: int = 320):
    packed = []
    for doc in documents:
        metadata = getattr(doc, "metadata", {}) or {}
        packed.append(
            {
                "title": doc.title,
                "source": doc.source,
                "language": doc.language,
                "category": doc.category,
                "metadata": {
                    "audience": metadata.get("audience", ""),
                    "role": metadata.get("role", ""),
                    "scenario": metadata.get("scenario", ""),
                    "intent": metadata.get("intent", ""),
                },
                "excerpt": (doc.content or "")[:max_chars],
            }
        )
    return packed


def _detect_product_type_intent(message: str):
    normalized = _normalize_text(message)
    intent_keywords = {
        "mobile": ["iphone", "android", "dien thoai", "mobile", "smartphone"],
        "computer": ["laptop", "notebook", "macbook", "pc", "may tinh", "computer"],
        "clothes": ["ao", "quan", "vay", "thoi trang", "clothes"],
        "tablet": ["tablet", "ipad", "may tinh bang"],
        "audio": ["tai nghe", "audio", "headphone", "loa"],
        "wearable": ["wearable", "smartwatch", "dong ho thong minh"],
        "component": ["linh kien", "ram", "cpu", "ssd", "gpu"],
        "peripheral": ["ban phim", "chuot", "peripheral", "keyboard", "mouse"],
        "monitor": ["man hinh", "monitor"],
        "accessory": ["phu kien dien thoai", "phu kien", "op lung", "dan man hinh"],
        "charging": ["sac", "charger", "cap sac", "pin du phong", "powerbank"],
        "book": ["sach", "book"],
    }

    best_type = "all"
    best_score = 0

    for product_type, keywords in intent_keywords.items():
        score = 0
        for token in keywords:
            if token in normalized:
                # Give slightly higher weight for longer/specific phrases.
                score += max(1, min(4, len(token.split())))

        if score > best_score:
            best_score = score
            best_type = product_type

    if best_score > 0:
        return best_type

    return "all"


def _catalog_documents_from_query(message: str, language: str = "vi", limit: int = 3):
    normalized_query = _normalize_text(message)
    terms = [
        term for term in re.findall(r"[a-z0-9]+", normalized_query) if len(term) >= 3
    ]
    if not terms:
        return []

    intent_type = _detect_product_type_intent(message)
    product_types = SUPPORTED_PRODUCT_TYPES.copy()
    if intent_type in SUPPORTED_PRODUCT_TYPE_SET:
        product_types = [intent_type] + [
            pt for pt in product_types if pt != intent_type
        ]

    candidates = []
    for product_type in product_types:
        for product in fetch_products(product_type, limit=40):
            name = str(product.get("name") or "")
            brand = str(product.get("brand") or "")
            description = str(product.get("description") or "")
            haystack = _normalize_text(" ".join([name, brand, description]))
            score = sum(
                2 if term in _normalize_text(name) else 1
                for term in terms
                if term in haystack
            )
            if score <= 0:
                continue

            content = (
                f"Ten san pham: {name}. "
                f"Thuong hieu: {brand or 'N/A'}. "
                f"Gia: {product.get('price')}. "
                f"Ton kho: {product.get('stock')}. "
                f"Mo ta: {description[:240]}."
            )
            candidates.append(
                (
                    score,
                    SimpleNamespace(
                        title=f"San pham {name}",
                        source=f"catalog:{product_type}:{product.get('id')}",
                        language=language,
                        category=product_type,
                        content=content,
                    ),
                )
            )

    if not candidates:
        return []

    candidates.sort(key=lambda row: row[0], reverse=True)
    selected = []
    seen_sources = set()
    for _, doc in candidates:
        if doc.source in seen_sources:
            continue
        seen_sources.add(doc.source)
        selected.append(doc)
        if len(selected) >= limit:
            break
    return selected


def _filter_documents_by_intent(documents, intent_type: str, limit: int = 6):
    if intent_type not in SUPPORTED_PRODUCT_TYPE_SET:
        return list(documents or [])[:limit]

    generic_categories = {"", "all", "policy", "faq", "operations"}
    filtered = []
    for doc in documents or []:
        category = str(getattr(doc, "category", "") or "").strip().lower()
        source = str(getattr(doc, "source", "") or "").strip().lower()
        if category == intent_type or category in generic_categories:
            filtered.append(doc)
            continue
        if source.startswith(f"catalog:{intent_type}:"):
            filtered.append(doc)

    if filtered:
        return filtered[:limit]
    return list(documents or [])[:limit]


def _build_rag_prompt(
    message: str, language: str, summary: dict, recommendations, context_docs
):
    return (
        "You are an e-commerce advisor assistant. "
        "Answer only from provided context and product recommendations. "
        "If evidence is insufficient, explicitly say that information is missing. "
        "Always include short citations in format [source:title].\n\n"
        f"Language: {language}\n"
        f"User message: {message}\n"
        f"Behavior summary: {json.dumps(summary, ensure_ascii=True)}\n"
        f"Context documents: {json.dumps(context_docs, ensure_ascii=True)}\n"
        f"Recommendations: {json.dumps([{'name': item.get('name'), 'product_type': item.get('product_type'), 'price': item.get('price')} for item in recommendations[:3]], ensure_ascii=True)}"
    )


def _insufficient_evidence_answer(language: str):
    if language.lower().startswith("en"):
        return "I do not have enough trusted context to answer this confidently. Please ask a more specific product or policy question."
    return "Toi chua co du ngu canh dang tin cay de tra loi chinh xac. Ban hay hoi cu the hon ve san pham hoac chinh sach."


def _fallback_chat_answer(message: str, docs, summary, recommendations, language: str):
    doc_titles = [
        str(getattr(doc, "title", "") or "Tai lieu tham khao") for doc in docs[:3]
    ]
    recommendation_lines = []
    for item in recommendations[:3]:
        name = str(item.get("name") or "San pham")
        price = item.get("price")
        if price is None or price == "":
            recommendation_lines.append(f"- {name}")
        else:
            recommendation_lines.append(f"- {name} (gia tham khao: {price})")

    if language.lower().startswith("en"):
        intro = "Here are practical suggestions based on available store data."
        recommendation_block = (
            "\n".join(recommendation_lines)
            if recommendation_lines
            else "- No matching products yet"
        )
        source_note = (
            f"Reference: {', '.join(doc_titles)}"
            if doc_titles
            else "Reference: Internal catalog data"
        )
        return (
            f"{intro}\n\nRecommended options:\n{recommendation_block}"
            + "\n\nIf you share your budget and main use, I can narrow this down to the best 2-3 choices for you."
            + f"\n\n{source_note}"
        )

    intro = "Minh goi y nhanh cho ban dua tren du lieu hien co:"
    recommendation_block = (
        "\n".join(recommendation_lines)
        if recommendation_lines
        else "- Hien chua co san pham phu hop"
    )
    source_note = (
        f"Thong tin tham khao: {', '.join(doc_titles)}"
        if doc_titles
        else "Thong tin tham khao: Du lieu catalog noi bo"
    )
    return (
        f"{intro}\n\n{recommendation_block}"
        + "\n\nNeu ban cho minh muc gia va nhu cau chinh (hoc tap, choi game, chup anh...), minh se loc ra 2-3 lua chon sat nhat."
        + f"\n\n{source_note}"
    )


@api_view(["POST"])
def track_event(request):
    serializer = TrackEventSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serializer.validated_data
    payload.setdefault("metadata", {})
    if not payload.get("user_id"):
        payload["user_id"] = request.META.get("HTTP_X_USER_ID", "")

    event = UserEvent.objects.create(**payload)
    return Response(
        {"status": "ok", "event_id": event.id}, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def trending_events(request):
    limit = int(request.query_params.get("limit", 6))
    return Response({"results": trending_products(limit=limit)})


@api_view(["POST"])
def keyword_suggestions(request):
    serializer = KeywordSuggestionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serializer.validated_data
    prefix = _normalize_text(payload.get("prefix", ""))
    if len(prefix) < 2:
        return Response({"results": []})

    product_type = (payload.get("product_type") or "all").lower()
    if product_type not in SUPPORTED_PRODUCT_TYPE_SET:
        product_type = "all"
    limit = payload.get("limit", 5)

    candidates = []
    candidates.extend(SEED_KEYWORDS.get("all", []))
    candidates.extend(SEED_KEYWORDS.get(product_type, []))

    event_query = (
        UserEvent.objects.exclude(query_text="")
        .exclude(query_text__isnull=True)
        .exclude(metadata__seeded=True)
    )
    session_id = payload.get("session_id", "")
    user_id = payload.get("user_id", "") or request.META.get("HTTP_X_USER_ID", "")
    if user_id:
        event_query = event_query.filter(user_id=user_id)
    elif session_id:
        event_query = event_query.filter(session_id=session_id)
    if product_type != "all":
        event_query = event_query.filter(product_type=product_type)

    query_terms = [
        (value or "").strip()
        for value in event_query.order_by("-created_at").values_list(
            "query_text", flat=True
        )[:120]
    ]
    candidates.extend(query_terms)

    kb_titles = list(
        retrieve_documents(prefix, language=payload.get("language", "vi"), limit=5)
    )
    candidates.extend(doc.title for doc in kb_titles if getattr(doc, "title", ""))

    frequencies = Counter(_normalize_text(term) for term in query_terms if term)
    scored = []
    seen = set()
    for term in candidates:
        value = (term or "").strip()
        normalized_value = _normalize_text(value)
        if not value or normalized_value in seen:
            continue
        if normalized_value.startswith(prefix):
            score = 100
        elif prefix in normalized_value:
            score = 65
        else:
            continue
        score += frequencies.get(normalized_value, 0) * 5
        score += max(0, 20 - abs(len(normalized_value) - len(prefix)))
        seen.add(normalized_value)
        scored.append((score, value))

    scored.sort(key=lambda item: item[0], reverse=True)
    return Response({"results": [term for _, term in scored[:limit]]})


@api_view(["POST"])
def recommendations(request):
    request_id = get_request_id()
    log_ctx = LogContext(logger, request_id=request_id, operation="recommendations")
    start = time.perf_counter()

    try:
        serializer = RecommendationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            log_ctx.warning("Validation failed", result_code=400)
            metrics.record_error("recommendations", "validation_error")
            return Response(
                {"error": "Validation failed", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = serializer.validated_data
        user_id = payload.get("user_id") or request.META.get("HTTP_X_USER_ID", "")
        session_id = payload.get("session_id", "")
        log_ctx.user_id = user_id

        summary, items = recommend_products(
            user_id=user_id,
            session_id=session_id,
            limit=payload.get("limit", 6),
            ranker_variant=payload.get("ranker_variant", "auto"),
            product_types=payload.get("product_types") or payload.get("product_type"),
        )

        duration_ms = (time.perf_counter() - start) * 1000
        log_ctx.info(
            f"Recommendation success, returned {len(items)} items",
            duration_ms=duration_ms,
            result_code=200,
        )
        metrics.record_latency("recommendations", duration_ms)

        if items:
            avg_score = sum(item.get("confidence", 0) for item in items) / len(items)
            metrics.record_confidence("recommendations", avg_score)

        diversity_stats = summary.get("diversity_stats", {})

        return Response(
            {
                "summary": summary,
                "results": items,
                "diversity_stats": diversity_stats,
            }
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_ctx.error(
            f"Recommendation failed: {e}", duration_ms=duration_ms, result_code=500
        )
        metrics.record_error("recommendations", "internal_error")
        return Response(
            {"status": "error", "detail": str(e), "request_id": request_id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def semantic_product_search(request):
    request_id = get_request_id()
    log_ctx = LogContext(logger, request_id=request_id, operation="semantic_search")
    start = time.perf_counter()

    serializer = SemanticSearchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        log_ctx.warning("Semantic search validation failed", result_code=400)
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serializer.validated_data
    user_id = payload.get("user_id") or request.META.get("HTTP_X_USER_ID", "")
    log_ctx.user_id = user_id

    items, mode = retrieve_products_graph(
        query=payload.get("query", ""),
        language=payload.get("language", "vi"),
        limit=payload.get("limit", 24),
        product_types=payload.get("product_types") or payload.get("product_type"),
        user_id=user_id,
        session_id=payload.get("session_id", ""),
    )

    duration_ms = (time.perf_counter() - start) * 1000
    log_ctx.info(
        f"Semantic search returned {len(items)} items",
        duration_ms=duration_ms,
        result_code=200,
        mode=mode,
    )
    metrics.record_latency("semantic_search", duration_ms)
    return Response({"results": items, "mode": mode})


@api_view(["POST"])
def chat(request):
    request_id = get_request_id()
    log_ctx = LogContext(logger, request_id=request_id, operation="chat")
    start_total = time.perf_counter()

    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        log_ctx.warning("Chat validation failed", result_code=400)
        metrics.record_error("chat", "validation_error")
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serializer.validated_data
    user_id = payload.get("user_id") or request.META.get("HTTP_X_USER_ID", "")
    session_id = payload.get("session_id", "")
    language = payload.get("language", "vi")
    log_ctx.user_id = user_id
    guardrail_blocked, guardrail_reason = _guardrail_check(payload["message"])
    if guardrail_blocked:
        _record_chat_metric(
            {
                "status": "blocked",
                "cache_hit": False,
                "retrieval_ms": 0.0,
                "generation_ms": 0.0,
                "total_ms": round((time.perf_counter() - start_total) * 1000, 2),
            }
        )
        return Response(
            {
                "answer": "Yeu cau khong phu hop voi chinh sach an toan. Vui long dat cau hoi ve san pham/chinh sach mua hang.",
                "used_cloud_model": False,
                "ai_status": "blocked",
                "guardrails": {"blocked": True, "reason": guardrail_reason},
                "context_documents": [],
                "sources": [],
                "rag": {
                    "version": "v2",
                    "retrieval_mode": get_retrieval_mode(),
                    "context_count": 0,
                },
                "summary": {},
                "recommendations": [],
            },
            status=status.HTTP_200_OK,
        )

    intent_type = _detect_product_type_intent(payload["message"])
    requested_types = intent_type if intent_type in SUPPORTED_PRODUCT_TYPE_SET else ""

    summary, recommendations_payload = recommend_products(
        user_id=user_id,
        session_id=session_id,
        limit=4,
        product_types=requested_types,
    )
    if requested_types:
        recommendations_payload = [
            item
            for item in recommendations_payload
            if str(item.get("product_type", "")).lower() == requested_types
        ]
        if len(recommendations_payload) > 4:
            recommendations_payload = recommendations_payload[:4]

    cache_key = _cache_key(
        payload["message"],
        language,
        payload.get("product_type", ""),
        payload.get("product_id"),
    )
    cache_hit = False
    if _is_trending_intent(payload["message"]):
        cached = cache.get(cache_key)
        if isinstance(cached, dict):
            cache_hit = True
            cached["cache"] = {"hit": True, "ttl_seconds": CACHE_TTL_SECONDS}
            _record_chat_metric(
                {
                    "status": cached.get("ai_status", "cached"),
                    "cache_hit": True,
                    "retrieval_ms": 0.0,
                    "generation_ms": 0.0,
                    "total_ms": round((time.perf_counter() - start_total) * 1000, 2),
                }
            )
            return Response(cached)

    retrieval_start = time.perf_counter()
    documents = list(retrieve_documents(payload["message"], language=language, limit=4))
    catalog_docs = _catalog_documents_from_query(
        payload["message"], language=language, limit=3
    )
    if catalog_docs:
        existing_sources = {getattr(doc, "source", "") for doc in documents}
        for doc in catalog_docs:
            if doc.source not in existing_sources:
                documents.append(doc)
    documents = _filter_documents_by_intent(documents, intent_type, limit=6)
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
    retrieval_mode = get_retrieval_mode()
    if catalog_docs:
        retrieval_mode = f"{retrieval_mode}+catalog"
    context_docs = _prepare_context_documents(documents)
    generation_ms = 0.0
    cloud_state = "not_attempted"

    if not context_docs:
        answer = _insufficient_evidence_answer(language)
        used_cloud = False
        ai_status = "no_evidence"
    else:
        prompt = _build_rag_prompt(
            message=payload["message"],
            language=language,
            summary=summary,
            recommendations=recommendations_payload,
            context_docs=context_docs,
        )
        generation_start = time.perf_counter()
        if _is_circuit_open():
            answer, used_cloud = "", False
            cloud_state = "circuit_open"
        else:
            answer, used_cloud, cloud_state, provider_status, provider_message = (
                _chat_completion(prompt)
            )
            if used_cloud:
                _register_cloud_success()
            else:
                _register_cloud_failure(cloud_state, provider_status, provider_message)
        generation_ms = (time.perf_counter() - generation_start) * 1000
        ai_status = "generated" if used_cloud else "fallback"

    if context_docs and not used_cloud:
        answer = _fallback_chat_answer(
            payload["message"], documents, summary, recommendations_payload, language
        )
        ai_status = "fallback"

    source_attribution = _build_source_attribution(documents)

    if context_docs and answer and not _is_answer_grounded(answer, documents):
        answer = "Toi khong tim duoc thong tin chinh xac"
        ai_status = "grounding_failed"
        used_cloud = False
        metrics.record_error("chat", "grounding_failed")
        log_ctx.warning("Chat grounding check failed", result_code=200)

    if used_cloud and source_attribution.get("text"):
        answer = f"{answer}\n\n{source_attribution['text']}"

    if session_id:
        UserEvent.objects.create(
            user_id=user_id,
            session_id=session_id,
            event_type="chat_message_sent",
            language=language,
            metadata={"message": payload["message"][:500], "used_cloud": used_cloud},
        )

    response_payload = {
        "answer": answer,
        "used_cloud_model": used_cloud,
        "ai_status": ai_status,
        "guardrails": {"blocked": False, "reason": ""},
        "cache": {"hit": cache_hit, "ttl_seconds": CACHE_TTL_SECONDS},
        "context_documents": [
            {
                "title": doc.title,
                "source": doc.source,
                "language": doc.language,
                "category": doc.category,
            }
            for doc in documents
        ],
        "sources": [
            {
                "title": doc.title,
                "source": doc.source,
                "language": doc.language,
                "category": doc.category,
            }
            for doc in documents
        ],
        "rag": {
            "version": "v2",
            "retrieval_mode": retrieval_mode,
            "context_count": len(documents),
            "cloud_state": cloud_state,
        },
        "summary": summary,
        "recommendations": recommendations_payload,
        "source_attribution": source_attribution,
        "metrics": {
            "retrieval_ms": round(retrieval_ms, 2),
            "generation_ms": round(generation_ms, 2),
            "total_ms": round((time.perf_counter() - start_total) * 1000, 2),
            "estimated_input_tokens": _estimate_tokens(payload["message"]),
            "estimated_output_tokens": _estimate_tokens(answer),
        },
    }

    if _is_trending_intent(payload["message"]) and context_docs:
        cache.set(cache_key, response_payload, timeout=CACHE_TTL_SECONDS)

    _record_chat_metric(
        {
            "status": ai_status,
            "cache_hit": cache_hit,
            "retrieval_ms": round(retrieval_ms, 2),
            "generation_ms": round(generation_ms, 2),
            "total_ms": round((time.perf_counter() - start_total) * 1000, 2),
        }
    )

    # Record metrics for Phase 6A observability
    total_ms = round((time.perf_counter() - start_total) * 1000, 2)
    metrics.record_latency("chat", total_ms)

    # Record confidence score for model quality tracking
    confidence_score = 0.95 if used_cloud else 0.7  # Cloud model more confident
    if not context_docs:
        confidence_score = 0.3  # Low confidence without evidence
    metrics.record_confidence("chat", confidence_score)

    # Record fallback usage for reliability tracking
    if ai_status == "fallback":
        metrics.record_fallback("retrieval")

    log_ctx.info(
        "Chat completed successfully",
        duration_ms=total_ms,
        result_code=200,
        extra={"ai_status": ai_status, "used_cloud": used_cloud},
    )

    return Response(response_payload)


@api_view(["GET"])
def ai_health(request):
    advisor_status = metrics.get_health_status()
    neo4j_connected = False
    behavior_manifest = {}
    try:
        from advisor.ml.kb_graph import get_neo4j_driver  # noqa: PLC0415

        neo4j_connected = get_neo4j_driver() is not None
    except Exception:  # noqa: BLE001
        neo4j_connected = False

    manifest_path = Path(settings.ARTIFACTS_DIR) / PRODUCTION_MODEL_MANIFEST
    if manifest_path.exists():
        try:
            behavior_manifest = json.loads(manifest_path.read_text())
        except (OSError, ValueError):
            behavior_manifest = {}

    return Response(
        {
            "status": "ok",
            "advisor_status": advisor_status,
            "retrieval_mode": get_retrieval_mode(),
            "behavior_model": {
                "selected_model": behavior_manifest.get("selected_model", "mlp"),
                "selection_basis": behavior_manifest.get(
                    "selection_basis", "metrics_fallback"
                ),
                "selected_model_score": behavior_manifest.get("selected_model_score"),
                "generated_at": behavior_manifest.get("generated_at"),
            },
            "neo4j": {
                "enabled": bool(getattr(settings, "NEO4J_ENABLED", True)),
                "connected": neo4j_connected,
                "uri": getattr(settings, "NEO4J_URI", ""),
            },
            "circuit_breaker": {
                "is_open": _is_circuit_open(),
                "consecutive_failures": CB_STATE["consecutive_failures"],
                "open_until": CB_STATE["open_until"],
                "last_error": CB_STATE["last_error"],
                "last_provider_status": CB_STATE["last_provider_status"],
                "last_provider_message": CB_STATE["last_provider_message"],
            },
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "llm": {
                "provider": getattr(settings, "LLM_PROVIDER", "openai"),
                "api_key_present": (
                    bool(getattr(settings, "GEMINI_API_KEY", ""))
                    if getattr(settings, "LLM_PROVIDER", "openai") == "gemini"
                    else bool(getattr(settings, "OPENAI_API_KEY", ""))
                ),
                "model": (
                    getattr(settings, "GEMINI_MODEL", "")
                    if getattr(settings, "LLM_PROVIDER", "openai") == "gemini"
                    else getattr(settings, "OPENAI_CHAT_MODEL", "")
                ),
            },
        }
    )


@api_view(["GET"])
def metrics_latest(request):
    """Alias endpoint for latest metrics snapshot."""
    return ai_metrics(request)


@api_view(["GET"])
def metrics_timeseries(request):
    """Return chat metrics points inside a rolling time window."""
    operation = (request.query_params.get("operation") or "chat").strip().lower()
    window_raw = (request.query_params.get("window") or "1h").strip().lower()

    window_seconds = 3600
    if window_raw.endswith("m"):
        try:
            window_seconds = int(window_raw[:-1]) * 60
        except ValueError:
            window_seconds = 3600
    elif window_raw.endswith("h"):
        try:
            window_seconds = int(window_raw[:-1]) * 3600
        except ValueError:
            window_seconds = 3600

    now = time.time()
    lower_bound = now - max(60, window_seconds)

    points = [
        row
        for row in list(CHAT_METRICS)
        if row.get("operation") == operation and row.get("timestamp", 0) >= lower_bound
    ]

    return Response(
        {
            "status": "ok",
            "operation": operation,
            "window": window_raw,
            "count": len(points),
            "points": points,
            "summary": _metrics_snapshot(),
        }
    )


@api_view(["GET"])
def ai_metrics(request):
    """Get current advisor metrics snapshot."""
    request_id = get_request_id()
    log_ctx = LogContext(logger, request_id=request_id, operation="metrics_snapshot")

    start = time.time()
    try:
        snapshot = metrics.get_snapshot()
        duration_ms = (time.time() - start) * 1000
        log_ctx.info(
            "Metrics endpoint called", duration_ms=duration_ms, result_code=200
        )
        metrics.record_latency("metrics_endpoint", duration_ms)

        return Response(
            {
                "request_id": request_id,
                "status": "ok",
                "metrics": snapshot,
                "health": metrics.get_health_status(),
            }
        )
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_ctx.error(
            f"Metrics endpoint error: {e}", duration_ms=duration_ms, result_code=500
        )
        metrics.record_error("metrics_endpoint", "internal_error")
        return Response(
            {"status": "error", "detail": str(e), "request_id": request_id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def ai_health_detailed(request):
    """Get detailed health status with metrics."""
    request_id = get_request_id()
    health_status = metrics.get_health_status()

    return Response(
        {
            "request_id": request_id,
            "status": health_status,
            "timestamp": time.time(),
            "uptime_seconds": metrics.get_snapshot().get("uptime_seconds", 0),
            "total_requests": metrics.get_snapshot().get("total_requests", 0),
            "error_rate": metrics.get_snapshot().get("error_rate", 0),
        }
    )


@api_view(["GET"])
def ai_report(request, report_key: str):
    report_map = {
        "model-comparison": Path(settings.ARTIFACTS_DIR)
        / "model_comparison_report.html",
        "benchmark": Path(settings.ARTIFACTS_DIR) / "advisor_benchmark_report.html",
    }
    target = report_map.get(str(report_key or "").strip().lower())
    if not target:
        return Response(
            {"status": "error", "detail": "Unknown report"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not target.exists():
        return Response(
            {"status": "error", "detail": f"Report not generated yet: {target.name}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        content = target.read_text(encoding="utf-8")
    except OSError as exc:
        return Response(
            {"status": "error", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return HttpResponse(content, content_type="text/html; charset=utf-8")
