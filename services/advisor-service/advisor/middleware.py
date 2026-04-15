import json
import time

from django.core.cache import cache
from django.http import JsonResponse


class AdvisorRateLimitMiddleware:
    """Simple in-memory rate limiting and session token budget control."""

    USER_LIMIT_PER_HOUR = 50
    SESSION_TOKEN_LIMIT = 500
    USER_WINDOW_SECONDS = 3600
    SESSION_WINDOW_SECONDS = 43200

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        payload = self._extract_payload(request)

        user_id = (
            request.META.get("HTTP_X_USER_ID")
            or payload.get("user_id")
            or request.GET.get("user_id")
            or request.META.get("REMOTE_ADDR")
            or "anonymous"
        )
        session_id = (
            request.META.get("HTTP_X_SESSION_ID")
            or payload.get("session_id")
            or request.GET.get("session_id")
            or ""
        )

        blocked = self._enforce_user_rate_limit(user_id)
        if blocked:
            return blocked

        blocked = self._enforce_session_token_budget(session_id, payload)
        if blocked:
            return blocked

        return self.get_response(request)

    def _extract_payload(self, request):
        if request.method not in {"POST", "PUT", "PATCH"}:
            return {}

        try:
            if not request.body:
                return {}
            body = request.body.decode("utf-8")
            data = json.loads(body)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _enforce_user_rate_limit(self, user_id):
        current_hour = int(time.time() // self.USER_WINDOW_SECONDS)
        key = f"advisor:rl:user:{user_id}:{current_hour}"

        if cache.get(key) is None:
            cache.set(key, 0, timeout=self.USER_WINDOW_SECONDS + 5)

        current_count = int(cache.get(key, 0))
        if current_count >= self.USER_LIMIT_PER_HOUR:
            return JsonResponse(
                {
                    "status": "error",
                    "code": "rate_limit_exceeded",
                    "detail": "Ban da vuot qua gioi han 50 requests/gio. Vui long thu lai sau.",
                },
                status=429,
            )

        cache.set(key, current_count + 1, timeout=self.USER_WINDOW_SECONDS + 5)
        return None

    def _enforce_session_token_budget(self, session_id, payload):
        if not session_id:
            return None

        estimated_tokens = self._estimate_tokens(payload)
        key = f"advisor:rl:session_tokens:{session_id}"
        used_tokens = int(cache.get(key, 0))

        if used_tokens + estimated_tokens > self.SESSION_TOKEN_LIMIT:
            return JsonResponse(
                {
                    "status": "error",
                    "code": "session_token_budget_exceeded",
                    "detail": "Session da vuot ngan sach 500 tokens. Vui long tao session moi de tiep tuc.",
                },
                status=429,
            )

        cache.set(
            key, used_tokens + estimated_tokens, timeout=self.SESSION_WINDOW_SECONDS
        )
        return None

    def _estimate_tokens(self, payload):
        text_parts = [
            str(payload.get("message", "")),
            str(payload.get("query_text", "")),
        ]
        text = " ".join(part for part in text_parts if part).strip()
        if not text:
            return 1

        # Coarse token estimate for cost guardrails.
        return max(1, len(text) // 4)
