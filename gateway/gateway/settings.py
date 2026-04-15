"""Gateway settings — no database needed."""

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
STAFF_SERVICE_URL = os.environ.get("STAFF_SERVICE_URL", "http://staff-service:8001")
CUSTOMER_SERVICE_URL = os.environ.get(
    "CUSTOMER_SERVICE_URL", "http://customer-service:8002"
)
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
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
