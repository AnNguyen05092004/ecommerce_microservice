#!/usr/bin/env python3
import argparse
import json
import re
import statistics
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error


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


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


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

            # --- Evidence-based / golden-set grounding ---
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
                source_recall = hits / len(expected_sources)
                source_precision_total += precision
                if hits > 0:
                    evidence_grounded_hits += 1

            expected_answer_keywords = item.get("expected_answer_keywords", [])
            semantic_recall = _semantic_keyword_recall(
                answer_text, expected_answer_keywords
            )
            if semantic_recall is not None:
                semantic_prompts += 1
                semantic_recall_total += semantic_recall

            expected_answer_phrases = item.get("expected_answer_phrases", [])
            exact_hit = _exact_phrase_hit(answer_text, expected_answer_phrases)
            if exact_hit is not None:
                exact_prompts += 1
                exact_hits += int(exact_hit)

            if source_recall is not None or semantic_recall is not None:
                combined_grounding_prompts += 1
                # Weighted score: prioritise evidence grounding, then semantic coverage.
                sr = source_recall if source_recall is not None else 0.0
                sem = semantic_recall if semantic_recall is not None else 0.0
                if source_recall is not None and semantic_recall is not None:
                    combined = 0.6 * sr + 0.4 * sem
                elif source_recall is not None:
                    combined = sr
                else:
                    combined = sem
                combined_grounding_total += combined
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
        # Evidence-based metrics (golden set)
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
        "golden_set_size": evidence_prompts,
        "semantic_eval_size": semantic_prompts,
        "exact_eval_size": exact_prompts,
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


def main():
    parser = argparse.ArgumentParser(description="Advisor baseline benchmark runner")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Gateway base URL",
    )
    parser.add_argument(
        "--config",
        default="docs/ai_benchmark_prompts.json",
        help="Benchmark config JSON path",
    )
    parser.add_argument(
        "--out",
        default="docs/reports/ai_baseline_report.json",
        help="Output report JSON path",
    )
    parser.add_argument(
        "--phase",
        default="phase-0-baseline",
        help="Phase label for the report (e.g. phase-0-baseline, phase-4-rag-v2)",
    )
    parser.add_argument(
        "--version",
        default="v1.0",
        help="Version tag for the report (e.g. v1.0, v2.1)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    chat_prompts = payload.get("chat_prompts", [])
    recommendation_cases = payload.get("recommendation_cases", [])

    if not chat_prompts:
        raise SystemExit("chat_prompts is empty")
    if not recommendation_cases:
        raise SystemExit("recommendation_cases is empty")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "phase": args.phase,
        "version": args.version,
        "chat": run_chat_benchmark(args.base_url, chat_prompts, recommendation_limit=6),
        "recommendations": run_recommendation_benchmark(
            args.base_url, recommendation_cases
        ),
        "notes": [
            "fallback_rate > 0 means cloud model was not used for some requests",
            "retrieval_relevance_at_k is measured by keyword hit in returned context_documents",
            "evidence_grounded_rate uses golden-set expected_sources; source_precision is precision@expected",
            "semantic_keyword_recall measures expected-answer keyword coverage in generated answer",
            "exact_phrase_hit_rate checks expected phrases for strict grounding",
            "combined_grounding_score blends source recall and semantic recall",
            "citation_rate/grounded_answer_rate are proxy metrics based on bracket presence",
        ],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Report written to: {out_path}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
