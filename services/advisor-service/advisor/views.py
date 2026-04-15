import json
import logging
import re
import time
from collections import Counter, deque
from types import SimpleNamespace
import unicodedata

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .logging_config import LogContext, setup_logging, get_request_id
from .ml.kb import get_retrieval_mode, retrieve_documents
from .ml.kb_graph import retrieve_products_graph
from .ml.metrics import get_metrics
from .ml.recommend import (
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
    if source:
        text = f"Dua tren: [{title}] - {source}"
    else:
        text = f"Dua tren: [{title}]"

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
    if any(
        token in normalized for token in ["iphone", "android", "dien thoai", "mobile"]
    ):
        return "mobile"
    if any(token in normalized for token in ["laptop", "notebook", "macbook", "pc"]):
        return "computer"
    if any(
        token in normalized for token in ["ao", "quan", "vay", "thoi trang", "clothes"]
    ):
        return "clothes"
    return "all"


def _catalog_documents_from_query(message: str, language: str = "vi", limit: int = 3):
    normalized_query = _normalize_text(message)
    terms = [
        term for term in re.findall(r"[a-z0-9]+", normalized_query) if len(term) >= 3
    ]
    if not terms:
        return []

    intent_type = _detect_product_type_intent(message)
    product_types = ["computer", "mobile", "clothes"]
    if intent_type in {"computer", "mobile", "clothes"}:
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
    doc_lines = [f"- {doc.title}: {doc.content[:180]}" for doc in docs[:3]]
    citations = [f"[{doc.source or 'kb'}:{doc.title}]" for doc in docs[:3]]
    if language.lower().startswith("en"):
        intro = (
            "I could not use the cloud model, so here is a grounded fallback answer."
        )
        behavior_line = f"Recent behavior: buy_score={summary['buy_score']}, top_categories={', '.join(summary['top_categories']) or 'none'}."
        recommendation_line = (
            ", ".join(item.get("name", "product") for item in recommendations[:3])
            or "No recommendation yet"
        )
        return (
            f"{intro}\n\n{behavior_line}\n\nRelevant knowledge:\n"
            + "\n".join(doc_lines)
            + f"\n\nSuggested products: {recommendation_line}."
            + (f"\n\nSources: {', '.join(citations)}" if citations else "")
        )

    intro = "Khong dung duoc cloud model nen day la cau tra loi fallback co neo theo du lieu hien co."
    behavior_line = f"Hanh vi gan day: buy_score={summary['buy_score']}, nhom quan tam={', '.join(summary['top_categories']) or 'chua ro'}."
    recommendation_line = (
        ", ".join(item.get("name", "san pham") for item in recommendations[:3])
        or "Chua co goi y"
    )
    return (
        f"{intro}\n\n{behavior_line}\n\nThong tin lien quan:\n"
        + "\n".join(doc_lines)
        + f"\n\nSan pham goi y: {recommendation_line}."
        + (f"\n\nNguon: {', '.join(citations)}" if citations else "")
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
    if product_type not in {"computer", "mobile", "clothes"}:
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

    summary, recommendations_payload = recommend_products(
        user_id=user_id, session_id=session_id, limit=4
    )

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

    if source_attribution.get("text"):
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
    return Response(
        {
            "status": "ok",
            "advisor_status": advisor_status,
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
