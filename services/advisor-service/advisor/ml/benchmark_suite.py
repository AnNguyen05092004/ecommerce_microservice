import json
import statistics
import time
import unicodedata
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib import error, request


BENCHMARK_REPORT_JSON = "advisor_benchmark_report.json"
BENCHMARK_REPORT_HTML = "advisor_benchmark_report.html"


def _post_json(url: str, payload: dict, timeout: int = 20):
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            elapsed_ms = (time.perf_counter() - start) * 1000
            parsed = json.loads(raw) if raw else {}
            return int(resp.status), parsed, elapsed_ms, ""
    except error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        detail = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), {}, elapsed_ms, detail
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - start) * 1000
        return 0, {}, elapsed_ms, str(exc)


def _percentile(values, p):
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    factor = rank - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * factor)


def _safe_contains_any(text: str, keywords):
    lowered = (text or "").lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _normalize_text(value: str):
    text = (value or "").strip().lower()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _semantic_keyword_recall(answer_text: str, expected_keywords):
    if not expected_keywords:
        return None
    normalized_answer = _normalize_text(answer_text)
    if not normalized_answer:
        return 0.0
    hits = 0
    for keyword in expected_keywords:
        token = _normalize_text(str(keyword))
        if token and token in normalized_answer:
            hits += 1
    return hits / max(1, len(expected_keywords))


def _exact_phrase_hit(answer_text: str, expected_phrases):
    if not expected_phrases:
        return None
    normalized_answer = _normalize_text(answer_text)
    return (
        1.0
        if any(
            _normalize_text(phrase) in normalized_answer for phrase in expected_phrases
        )
        else 0.0
    )


def run_chat_benchmark(base_url: str, prompts, recommendation_limit: int):
    latencies = []
    fallback_count = 0
    success_count = 0
    failures = []
    relevance_hits = 0
    grounded_hits = 0
    citation_hits = 0
    hallucination_proxy_hits = 0
    evidence_grounded_hits = 0
    source_precision_total = 0.0
    evidence_prompts = 0
    semantic_recall_total = 0.0
    semantic_prompts = 0
    exact_hits = 0
    exact_prompts = 0
    combined_grounding_total = 0.0
    combined_grounding_prompts = 0

    for idx, item in enumerate(prompts, start=1):
        payload = {
            "session_id": f"bench-chat-{idx}",
            "user_id": "bench-user-01",
            "message": item["message"],
            "language": item.get("language", "vi"),
        }
        status_code, data, elapsed_ms, error_text = _post_json(
            f"{base_url}/api/advisor-service/chat/", payload
        )
        latencies.append(elapsed_ms)

        if status_code == 200 and isinstance(data, dict):
            success_count += 1
            if not data.get("used_cloud_model", False):
                fallback_count += 1

            context_docs = data.get("context_documents", [])
            blob = " ".join(
                f"{doc.get('title', '')} {doc.get('source', '')}"
                for doc in context_docs
                if isinstance(doc, dict)
            )
            if _safe_contains_any(blob, item.get("expected_doc_keywords", [])):
                relevance_hits += 1

            answer_text = str(data.get("answer", ""))
            has_context = bool(context_docs)
            has_citation = "[" in answer_text and "]" in answer_text
            if has_context and has_citation:
                grounded_hits += 1
            if has_citation:
                citation_hits += 1
            if has_context and not has_citation and answer_text:
                hallucination_proxy_hits += 1

            expected_sources = item.get("expected_sources", [])
            source_recall = None
            if expected_sources:
                evidence_prompts += 1
                actual_sources = [
                    (doc.get("source") or "").lower()
                    for doc in data.get("sources", context_docs)
                    if isinstance(doc, dict)
                ]
                hits = sum(
                    1
                    for exp in expected_sources
                    if any(exp.lower() in actual for actual in actual_sources)
                )
                precision = hits / len(expected_sources)
                source_precision_total += precision
                source_recall = hits / len(expected_sources)
                if hits > 0:
                    evidence_grounded_hits += 1

            semantic_recall = _semantic_keyword_recall(
                answer_text, item.get("expected_answer_keywords", [])
            )
            if semantic_recall is not None:
                semantic_prompts += 1
                semantic_recall_total += semantic_recall

            exact_hit = _exact_phrase_hit(
                answer_text, item.get("expected_answer_phrases", [])
            )
            if exact_hit is not None:
                exact_prompts += 1
                exact_hits += int(exact_hit)

            if source_recall is not None or semantic_recall is not None:
                combined_grounding_prompts += 1
                sr = source_recall if source_recall is not None else 0.0
                sem = semantic_recall if semantic_recall is not None else 0.0
                combined_grounding_total += (
                    0.6 * sr + 0.4 * sem
                    if source_recall is not None and semantic_recall is not None
                    else (sr or sem)
                )
        else:
            failures.append(
                {
                    "message": item["message"],
                    "status_code": status_code,
                    "error": error_text[:300],
                }
            )

    total = len(prompts)
    return {
        "sample_size": total,
        "success_count": success_count,
        "failure_count": total - success_count,
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0,
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "p50": round(_percentile(latencies, 0.50), 2),
            "p95": round(_percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "fallback_rate": round(fallback_count / total, 4) if total else 0,
        "retrieval_relevance_at_k": round(relevance_hits / total, 4) if total else 0,
        "grounded_answer_rate": round(grounded_hits / total, 4) if total else 0,
        "citation_rate": round(citation_hits / total, 4) if total else 0,
        "hallucination_proxy_rate": (
            round(hallucination_proxy_hits / total, 4) if total else 0
        ),
        "evidence_grounded_rate": (
            round(evidence_grounded_hits / evidence_prompts, 4)
            if evidence_prompts
            else None
        ),
        "source_precision": (
            round(source_precision_total / evidence_prompts, 4)
            if evidence_prompts
            else None
        ),
        "semantic_keyword_recall": (
            round(semantic_recall_total / semantic_prompts, 4)
            if semantic_prompts
            else None
        ),
        "exact_phrase_hit_rate": (
            round(exact_hits / exact_prompts, 4) if exact_prompts else None
        ),
        "combined_grounding_score": (
            round(combined_grounding_total / combined_grounding_prompts, 4)
            if combined_grounding_prompts
            else None
        ),
        "recommendation_limit": recommendation_limit,
        "failures": failures,
    }


def run_recommendation_benchmark(base_url: str, recommendation_cases):
    latencies = []
    success_count = 0
    valid_result_count = 0
    failures = []
    for idx, item in enumerate(recommendation_cases, start=1):
        payload = {
            "session_id": f"bench-rec-{idx}",
            "user_id": "bench-user-01",
            "limit": item.get("limit", 6),
            "product_type": item.get("product_type", ""),
        }
        status_code, data, elapsed_ms, error_text = _post_json(
            f"{base_url}/api/advisor-service/recommendations/", payload
        )
        latencies.append(elapsed_ms)
        if status_code == 200 and isinstance(data, dict):
            success_count += 1
            results = data.get("results", [])
            if isinstance(results, list) and results:
                valid_result_count += 1
        else:
            failures.append(
                {
                    "limit": payload["limit"],
                    "status_code": status_code,
                    "error": error_text[:300],
                }
            )

    total = len(recommendation_cases)
    return {
        "sample_size": total,
        "success_count": success_count,
        "failure_count": total - success_count,
        "non_empty_result_rate": round(valid_result_count / total, 4) if total else 0,
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0,
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "p50": round(_percentile(latencies, 0.50), 2),
            "p95": round(_percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "failures": failures,
    }


def run_semantic_benchmark(base_url: str, semantic_cases):
    latencies = []
    success_count = 0
    non_empty_count = 0
    correct_type_hits = 0
    min_count_hits = 0
    failures = []
    for idx, item in enumerate(semantic_cases, start=1):
        payload = {
            "session_id": f"bench-sem-{idx}",
            "user_id": "bench-user-01",
            "query": item["query"],
            "language": item.get("language", "vi"),
            "product_type": item.get("product_type", ""),
            "limit": item.get("limit", 6),
        }
        status_code, data, elapsed_ms, error_text = _post_json(
            f"{base_url}/api/advisor-service/search/semantic/", payload
        )
        latencies.append(elapsed_ms)
        if status_code == 200 and isinstance(data, dict):
            success_count += 1
            results = data.get("results", [])
            if isinstance(results, list) and results:
                non_empty_count += 1
                expected_types = [
                    str(value).lower()
                    for value in item.get("expected_product_types", [])
                ]
                if expected_types and any(
                    str(row.get("product_type", "")).lower() in expected_types
                    for row in results
                ):
                    correct_type_hits += 1
                if len(results) >= int(item.get("min_results", 1)):
                    min_count_hits += 1
        else:
            failures.append(
                {
                    "query": payload["query"],
                    "status_code": status_code,
                    "error": error_text[:300],
                }
            )

    total = len(semantic_cases)
    return {
        "sample_size": total,
        "success_count": success_count,
        "failure_count": total - success_count,
        "non_empty_result_rate": round(non_empty_count / total, 4) if total else 0,
        "correct_type_rate": round(correct_type_hits / total, 4) if total else 0,
        "min_results_hit_rate": round(min_count_hits / total, 4) if total else 0,
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0,
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "p50": round(_percentile(latencies, 0.50), 2),
            "p95": round(_percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "failures": failures,
    }


def generate_benchmark_html(report: dict) -> str:
    chat = report.get("chat", {})
    recommendations = report.get("recommendations", {})
    semantic = report.get("semantic_search", {})
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Advisor Benchmark Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; background: #f8fafc; color: #111827; }}
    .hero {{ background: linear-gradient(135deg, #059669, #0f766e); color: white; padding: 24px; border-radius: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 24px 0; }}
    .card {{ background: white; border-radius: 16px; padding: 18px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 16px; overflow: hidden; margin-top: 16px; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
    th {{ background: #ecfeff; }}
  </style>
</head>
<body>
  <div class="hero">
    <h1>Advisor Evaluation Report</h1>
    <p>Generated at {generated_at}</p>
    <p>Phase: {phase} • Version: {version}</p>
  </div>
  <div class="grid">
    <div class="card"><strong>Chat Success</strong><div>{chat_success}</div></div>
    <div class="card"><strong>Recommendation Non-empty</strong><div>{rec_non_empty}</div></div>
    <div class="card"><strong>Semantic Correct Type</strong><div>{sem_type}</div></div>
    <div class="card"><strong>Chat p95</strong><div>{chat_p95} ms</div></div>
  </div>
  <table>
    <thead><tr><th>Suite</th><th>Success</th><th>Failure</th><th>Primary Metric</th><th>p95 Latency</th></tr></thead>
    <tbody>
      <tr><td>Chat</td><td>{chat_success}</td><td>{chat_failure}</td><td>{chat_primary}</td><td>{chat_p95}</td></tr>
      <tr><td>Recommendations</td><td>{rec_success}</td><td>{rec_failure}</td><td>{rec_primary}</td><td>{rec_p95}</td></tr>
      <tr><td>Semantic Search</td><td>{sem_success}</td><td>{sem_failure}</td><td>{sem_primary}</td><td>{sem_p95}</td></tr>
    </tbody>
  </table>
</body>
</html>
    """.format(
        generated_at=escape(str(report.get("generated_at", ""))),
        phase=escape(str(report.get("phase", ""))),
        version=escape(str(report.get("version", ""))),
        chat_success=escape(str(chat.get("success_count", 0))),
        chat_failure=escape(str(chat.get("failure_count", 0))),
        chat_primary=escape(str(chat.get("combined_grounding_score", "-"))),
        chat_p95=escape(str((chat.get("latency_ms") or {}).get("p95", 0))),
        rec_success=escape(str(recommendations.get("success_count", 0))),
        rec_failure=escape(str(recommendations.get("failure_count", 0))),
        rec_non_empty=escape(str(recommendations.get("non_empty_result_rate", 0))),
        rec_primary=escape(str(recommendations.get("non_empty_result_rate", 0))),
        rec_p95=escape(str((recommendations.get("latency_ms") or {}).get("p95", 0))),
        sem_success=escape(str(semantic.get("success_count", 0))),
        sem_failure=escape(str(semantic.get("failure_count", 0))),
        sem_type=escape(str(semantic.get("correct_type_rate", 0))),
        sem_primary=escape(str(semantic.get("correct_type_rate", 0))),
        sem_p95=escape(str((semantic.get("latency_ms") or {}).get("p95", 0))),
    )


def run_benchmark_suite(
    base_url: str, config: dict, out_dir: Path, phase: str, version: str
) -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "phase": phase,
        "version": version,
        "chat": run_chat_benchmark(
            base_url, config.get("chat_prompts", []), recommendation_limit=6
        ),
        "recommendations": run_recommendation_benchmark(
            base_url, config.get("recommendation_cases", [])
        ),
        "semantic_search": run_semantic_benchmark(
            base_url, config.get("semantic_cases", [])
        ),
        "notes": [
            "chat.combined_grounding_score blends expected source recall and semantic recall",
            "recommendations.non_empty_result_rate tracks recommendation usefulness",
            "semantic_search.correct_type_rate checks semantic retrieval returns expected product types",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / BENCHMARK_REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / BENCHMARK_REPORT_HTML).write_text(
        generate_benchmark_html(report), encoding="utf-8"
    )
    return report
