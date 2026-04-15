import jwt
import json
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

# File này là người bảo vệ cửa — ai muốn vào service đích phải trình token hợp lệ, sau đó được chuyển tiếp request tới đúng nơi.

# ── Routes that DO NOT require authentication ────────────
PUBLIC_ROUTES = [
    # Staff
    "api/auth/login/",
    # Customer
    "api/auth/login/",
    "api/auth/register/",
    # Advisor
    "api/events/track/",
    "api/events/trending/",
    "api/search/suggest/",
    "api/search/semantic/",
    "api/recommendations/",
    "api/chat/",
    # Products (GET only)
    "api/computers/",
    "api/mobiles/",
    "api/categories/",
    # Reviews (GET only)
    "api/reviews/",
]


def is_public_route(path, method):
    """Check if the route is public (no auth needed)"""
    # Auth endpoints are always public
    if "auth/login" in path or "auth/register" in path or "auth/verify" in path:
        return True

    # GET requests to product listings and categories are public
    if method == "GET":
        public_prefixes = [
            "computers",
            "mobiles",
            "clothes",
            "tablets",
            "audios",
            "wearables",
            "components",
            "peripherals",
            "monitors",
            "accessories",
            "chargings",
            "books",
            "categories",
            "reviews",
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


@csrf_exempt
def proxy_staff_service(request, path):
    return gateway_view(request, path, settings.STAFF_SERVICE_URL)


@csrf_exempt
def proxy_customer_service(request, path):
    return gateway_view(request, path, settings.CUSTOMER_SERVICE_URL)


@csrf_exempt
def proxy_computer_service(request, path):
    return gateway_view(request, path, settings.COMPUTER_SERVICE_URL)


@csrf_exempt
def proxy_mobile_service(request, path):
    return gateway_view(request, path, settings.MOBILE_SERVICE_URL)


@csrf_exempt
def proxy_clothes_service(request, path):
    return gateway_view(request, path, settings.CLOTHES_SERVICE_URL)


@csrf_exempt
def proxy_tablet_service(request, path):
    return gateway_view(request, path, settings.TABLET_SERVICE_URL)


@csrf_exempt
def proxy_audio_service(request, path):
    return gateway_view(request, path, settings.AUDIO_SERVICE_URL)


@csrf_exempt
def proxy_wearable_service(request, path):
    return gateway_view(request, path, settings.WEARABLE_SERVICE_URL)


@csrf_exempt
def proxy_component_service(request, path):
    return gateway_view(request, path, settings.COMPONENT_SERVICE_URL)


@csrf_exempt
def proxy_peripheral_service(request, path):
    return gateway_view(request, path, settings.PERIPHERAL_SERVICE_URL)


@csrf_exempt
def proxy_monitor_service(request, path):
    return gateway_view(request, path, settings.MONITOR_SERVICE_URL)


@csrf_exempt
def proxy_accessory_service(request, path):
    return gateway_view(request, path, settings.ACCESSORY_SERVICE_URL)


@csrf_exempt
def proxy_charging_service(request, path):
    return gateway_view(request, path, settings.CHARGING_SERVICE_URL)


@csrf_exempt
def proxy_book_service(request, path):
    return gateway_view(request, path, settings.BOOK_SERVICE_URL)


@csrf_exempt
def proxy_advisor_service(request, path):
    return gateway_view(request, path, settings.ADVISOR_SERVICE_URL)
