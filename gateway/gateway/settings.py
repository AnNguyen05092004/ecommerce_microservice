"""Gateway settings — no database needed."""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "corsheaders",
    "proxy",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = "gateway.urls"
WSGI_APPLICATION = "gateway.wsgi.application"

# No database for gateway
DATABASES = {}

# JWT
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret")

# Service URLs
ADVISOR_SERVICE_URL = os.environ.get(
    "ADVISOR_SERVICE_URL", "http://advisor-service:8006"
)
IDENTITY_SERVICE_URL = os.environ.get(
    "IDENTITY_SERVICE_URL", "http://identity-service:8016"
)
PRODUCT_SERVICE_URL = os.environ.get(
    "PRODUCT_SERVICE_URL", "http://product-service:8017"
)
INVENTORY_SERVICE_URL = os.environ.get(
    "INVENTORY_SERVICE_URL", "http://inventory-service:8018"
)
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://cart-service:8019")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8020")
PAYMENT_SERVICE_URL = os.environ.get(
    "PAYMENT_SERVICE_URL", "http://payment-service:8021"
)
REVIEW_SERVICE_URL = os.environ.get("REVIEW_SERVICE_URL", "http://review-service:8022")
STAFF_SERVICE_URL = os.environ.get("STAFF_SERVICE_URL", "http://staff-service:8001")
CUSTOMER_SERVICE_URL = os.environ.get(
    "CUSTOMER_SERVICE_URL", "http://customer-service:8002"
)


def _load_service_registry():
    defaults = {
        "advisor-service": ADVISOR_SERVICE_URL,
        "identity-service": IDENTITY_SERVICE_URL,
        "product-service": PRODUCT_SERVICE_URL,
        "inventory-service": INVENTORY_SERVICE_URL,
        "cart-service": CART_SERVICE_URL,
        "order-service": ORDER_SERVICE_URL,
        "payment-service": PAYMENT_SERVICE_URL,
        "review-service": REVIEW_SERVICE_URL,
        "staff-service": STAFF_SERVICE_URL,
        "customer-service": CUSTOMER_SERVICE_URL,
        # Bounded-context facades
        "identity": IDENTITY_SERVICE_URL,
        "catalog": PRODUCT_SERVICE_URL,
        "inventory": INVENTORY_SERVICE_URL,
        "cart": CART_SERVICE_URL,
        "orders": ORDER_SERVICE_URL,
        "payments": PAYMENT_SERVICE_URL,
        "reviews": REVIEW_SERVICE_URL,
        "staff": STAFF_SERVICE_URL,
        "customer": CUSTOMER_SERVICE_URL,
        "advisor": ADVISOR_SERVICE_URL,
    }

    raw = os.environ.get("SERVICES_REGISTRY", "").strip()
    if not raw:
        return defaults

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return defaults

    if not isinstance(parsed, dict):
        return defaults

    cleaned = {
        str(name): str(url)
        for name, url in parsed.items()
        if isinstance(name, str) and isinstance(url, str) and url
    }
    defaults.update(cleaned)
    return defaults


SERVICE_REGISTRY = _load_service_registry()

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
