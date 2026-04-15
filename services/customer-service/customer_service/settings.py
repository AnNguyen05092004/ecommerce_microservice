"""Django settings for customer_service project."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "corsheaders",
    "authentication",
    "customers",
    "cart",
    "orders",
    "reviews",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = "customer_service.urls"
WSGI_APPLICATION = "customer_service.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "customer_db"),
        "USER": os.environ.get("DB_USER", "customer_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "customer_password"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret")
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))

# Inter-service URLs
COMPUTER_SERVICE_URL = os.environ.get(
    "COMPUTER_SERVICE_URL", "http://computer-service:8003"
)
MOBILE_SERVICE_URL = os.environ.get("MOBILE_SERVICE_URL", "http://mobile-service:8004")
CLOTHES_SERVICE_URL = os.environ.get(
    "CLOTHES_SERVICE_URL", "http://clothes-service:8005"
)
TABLET_SERVICE_URL = os.environ.get("TABLET_SERVICE_URL", "http://tablet-service:8007")
AUDIO_SERVICE_URL = os.environ.get("AUDIO_SERVICE_URL", "http://audio-service:8008")
WEARABLE_SERVICE_URL = os.environ.get(
    "WEARABLE_SERVICE_URL", "http://wearable-service:8009"
)
COMPONENT_SERVICE_URL = os.environ.get(
    "COMPONENT_SERVICE_URL", "http://component-service:8010"
)
PERIPHERAL_SERVICE_URL = os.environ.get(
    "PERIPHERAL_SERVICE_URL", "http://peripheral-service:8011"
)
MONITOR_SERVICE_URL = os.environ.get(
    "MONITOR_SERVICE_URL", "http://monitor-service:8012"
)
ACCESSORY_SERVICE_URL = os.environ.get(
    "ACCESSORY_SERVICE_URL", "http://accessory-service:8013"
)
CHARGING_SERVICE_URL = os.environ.get(
    "CHARGING_SERVICE_URL", "http://charging-service:8014"
)
BOOK_SERVICE_URL = os.environ.get("BOOK_SERVICE_URL", "http://book-service:8015")
ADVISOR_SERVICE_URL = os.environ.get(
    "ADVISOR_SERVICE_URL", "http://advisor-service:8006"
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
