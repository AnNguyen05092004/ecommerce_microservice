import jwt
import json
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

# File này là người bảo vệ cửa — ai muốn vào service đích phải trình token hợp lệ, sau đó được chuyển tiếp request tới đúng nơi.

# ── Routes that DO NOT require authentication ────────────
PUBLIC_ROUTES = []


def is_public_route(path, method):
    """Check if the route is public (no auth needed)"""
    if path == "health":
        return True

    # Auth endpoints are always public
    if "auth/login" in path or "auth/register" in path or "auth/verify" in path:
        return True

    # Public read endpoints for DDD-only stack
    if method == "GET":
        public_prefixes = [
            "products",
            "product-types",
            "categories",
            "reviews",
            "inventory",
            "carts",
            "orders",
            "payments",
            "events/trending",
            "ai/health",
            "ai/metrics",
        ]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True

    if method == "POST":
        public_prefixes = [
            "events/track",
            "search/suggest",
            "search/semantic",
            "recommendations",
            "chat",
            "inventory",
            "carts",
            "orders",
            "payments",
            "reviews",
        ]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True

    if method == "PATCH":
        public_prefixes = [
            "carts/",
            "orders/",
            "payments/",
            "reviews/",
            "inventory/",
        ]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True

    return False


def verify_jwt_token(token):
    """Verify JWT token locally"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def forward_request(request, target_url, path):
    """Forward the request to the target service"""
    if path == "health":
        url = f"{target_url}/health"
    else:
        url = f"{target_url}/api/{path}"

    # Prepare headers
    headers = {
        "Content-Type": request.content_type or "application/json",
    }

    # Forward auth user info if available
    if hasattr(request, "_jwt_payload"):
        payload = request._jwt_payload
        headers["X-User-ID"] = str(payload.get("user_id", ""))
        headers["X-Username"] = str(payload.get("username", ""))
        headers["X-User-Type"] = str(payload.get("user_type", ""))
        headers["X-User-Role"] = str(payload.get("role", ""))

    # Forward the Authorization header as well
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header:
        headers["Authorization"] = auth_header

    try:
        method = request.method.lower()
        kwargs = {
            "url": url,
            "headers": headers,
            "timeout": 30,
            "params": request.GET.dict(),
        }

        # Add body for non-GET requests
        if method in ("post", "put", "patch", "delete"):
            kwargs["data"] = request.body

        response = getattr(requests, method)(**kwargs)

        # Create Django response from service response
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/json"),
        )
        return django_response

    except requests.ConnectionError:
        return JsonResponse(
            {
                "error": "Service unavailable",
                "detail": f"Cannot connect to service at {target_url}",
            },
            status=503,
        )
    except requests.Timeout:
        return JsonResponse(
            {"error": "Service timeout", "detail": "Request timed out"}, status=504
        )


def gateway_view(request, path, service_url):
    """Generic gateway view handler"""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    public_route = is_public_route(path, request.method)
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = verify_jwt_token(token)
        if not payload:
            if public_route:
                return forward_request(request, service_url, path)
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        request._jwt_payload = payload
    elif not public_route:
        return JsonResponse({"error": "Authentication required"}, status=401)

    return forward_request(request, service_url, path)


def _resolve_service_url(service_name):
    registry = getattr(settings, "SERVICE_REGISTRY", {}) or {}
    return registry.get(service_name)


@csrf_exempt
def proxy_service(request, service_name, path):
    service_url = _resolve_service_url(service_name)
    if not service_url:
        return JsonResponse(
            {
                "error": "Unknown service",
                "detail": f"Service '{service_name}' is not registered",
            },
            status=404,
        )
    return gateway_view(request, path, service_url)


def _proxy_context(request, path, service_key):
    return proxy_service(request, service_key, path)


@csrf_exempt
def proxy_identity_context(request, path):
    return _proxy_context(request, path, "identity")


@csrf_exempt
def proxy_catalog_context(request, path):
    return _proxy_context(request, path, "catalog")


@csrf_exempt
def proxy_inventory_context(request, path):
    return _proxy_context(request, path, "inventory")


@csrf_exempt
def proxy_cart_context(request, path):
    return _proxy_context(request, path, "cart")


@csrf_exempt
def proxy_orders_context(request, path):
    return _proxy_context(request, path, "orders")


@csrf_exempt
def proxy_payments_context(request, path):
    return _proxy_context(request, path, "payments")


@csrf_exempt
def proxy_reviews_context(request, path):
    return _proxy_context(request, path, "reviews")


@csrf_exempt
def proxy_advisor_context(request, path):
    return _proxy_context(request, path, "advisor")
