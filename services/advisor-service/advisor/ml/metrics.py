import time
from collections import defaultdict, deque
from statistics import mean, quantiles


class LatencyTracker:
    """Track latency metrics (p50, p95, p99)."""

    def __init__(self, max_records=1000):
        self.max_records = max_records
        self.latencies = deque(maxlen=max_records)

    def record(self, duration_ms):
        """Record a latency measurement in milliseconds."""
        self.latencies.append(duration_ms)

    def get_stats(self):
        """Return latency statistics."""
        if len(self.latencies) == 0:
            return {"count": 0, "p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}

        sorted_vals = sorted(self.latencies)
        count = len(sorted_vals)

        # Calculate percentiles
        if count >= 2:
            quantiles_result = quantiles(sorted_vals, n=100)  # 99 cut points
            p50 = quantiles_result[49]  # 50th percentile
            p95 = quantiles_result[94]  # 95th percentile
            p99 = quantiles_result[98]  # 99th percentile
        else:
            p50 = p95 = p99 = sorted_vals[0] if sorted_vals else 0

        return {
            "count": count,
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "min": round(min(sorted_vals), 2),
            "max": round(max(sorted_vals), 2),
            "avg": round(mean(sorted_vals), 2),
        }


class ErrorCounter:
    """Track error counts and rates."""

    def __init__(self, max_records=1000):
        self.max_records = max_records
        self.errors = deque(maxlen=max_records)
        self.error_codes = defaultdict(int)

    def record(self, error_code):
        """Record an error."""
        self.errors.append(error_code)
        self.error_codes[error_code] += 1

    def get_stats(self):
        """Return error statistics."""
        total = len(self.errors)
        if total == 0:
            return {"total": 0, "rate": 0.0, "by_code": {}}

        return {
            "total": total,
            "rate": round(100.0 * total / max(total, 100), 2),  # Avoid division
            "by_code": dict(self.error_codes),
        }


class ConfidenceTracker:
    """Track prediction confidence distribution."""

    def __init__(self, max_records=1000):
        self.max_records = max_records
        self.confidences = deque(maxlen=max_records)
        self.buckets = defaultdict(int)  # 0.0, 0.1, 0.2, ... 1.0

    def record(self, score):
        """Record a confidence score (0.0-1.0)."""
        self.confidences.append(score)
        bucket = int(score * 10) / 10.0
        self.buckets[round(bucket, 1)] += 1

    def get_stats(self):
        """Return confidence distribution."""
        if not self.confidences:
            return {"count": 0, "avg": 0.0, "distribution": {}}

        avg_conf = round(mean(self.confidences), 2)
        dist = {k: v for k, v in sorted(self.buckets.items())}

        return {
            "count": len(self.confidences),
            "avg": avg_conf,
            "distribution": dist,
        }


class MetricsCollector:
    """Central metrics collection for advisor service."""

    def __init__(self):
        self.latencies = defaultdict(lambda: LatencyTracker())
        self.errors = defaultdict(lambda: ErrorCounter())
        self.confidence = defaultdict(lambda: ConfidenceTracker())
        self.fallback_count = defaultdict(int)
        self.cache_hits = defaultdict(int)
        self.cache_misses = defaultdict(int)
        self.start_time = time.time()

    def record_latency(self, operation, duration_ms):
        """Record latency for an operation."""
        self.latencies[operation].record(duration_ms)

    def record_error(self, operation, error_code):
        """Record an error."""
        self.errors[operation].record(error_code)

    def record_confidence(self, operation, score):
        """Record prediction confidence."""
        self.confidence[operation].record(score)

    def record_fallback(self, operation):
        """Record fallback usage."""
        self.fallback_count[operation] += 1

    def record_cache_hit(self, operation):
        """Record cache hit."""
        self.cache_hits[operation] += 1

    def record_cache_miss(self, operation):
        """Record cache miss."""
        self.cache_misses[operation] += 1

    def get_snapshot(self):
        """Get current metrics snapshot."""
        total_requests = sum(s.get_stats()["count"] for s in self.latencies.values())
        total_errors = sum(e.get_stats()["total"] for e in self.errors.values())

        latency_stats = {
            op: tracker.get_stats() for op, tracker in self.latencies.items()
        }
        error_stats = {op: tracker.get_stats() for op, tracker in self.errors.items()}
        confidence_stats = {
            op: tracker.get_stats() for op, tracker in self.confidence.items()
        }

        uptime_seconds = int(time.time() - self.start_time)

        return {
            "timestamp": time.time(),
            "uptime_seconds": uptime_seconds,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(100.0 * total_errors / max(total_requests, 1), 2),
            "latency": latency_stats,
            "errors": error_stats,
            "confidence": confidence_stats,
            "fallback": dict(self.fallback_count),
            "cache": {
                "hits": dict(self.cache_hits),
                "misses": dict(self.cache_misses),
            },
        }

    def get_health_status(self):
        """Determine service health based on metrics."""
        snapshot = self.get_snapshot()
        error_rate = snapshot.get("error_rate", 0)

        if error_rate > 10:
            return "error"
        elif error_rate > 5:
            return "degraded"
        else:
            return "ok"

    def reset(self):
        """Reset all metrics."""
        self.latencies.clear()
        self.errors.clear()
        self.confidence.clear()
        self.fallback_count.clear()
        self.cache_hits.clear()
        self.cache_misses.clear()
        self.start_time = time.time()


# Global metrics instance
global_metrics = MetricsCollector()


def get_metrics():
    """Get global metrics collector."""
    return global_metrics
