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
    "advisor",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "advisor.middleware.AdvisorRateLimitMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = "advisor_service.urls"
WSGI_APPLICATION = "advisor_service.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_PATH", str(BASE_DIR / "data" / "advisor.sqlite3")),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", str(BASE_DIR / "artifacts")))
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

KB_BOOTSTRAP_PATH = Path(
    os.environ.get(
        "KB_BOOTSTRAP_PATH",
        str(BASE_DIR / "advisor" / "knowledge_base" / "default_documents.json"),
    )
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
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
RECOMMENDER_AB_ENABLED = os.environ.get("RECOMMENDER_AB_ENABLED", "False").lower() in (
    "true",
    "1",
    "yes",
)
RECOMMENDER_DEFAULT_VARIANT = os.environ.get("RECOMMENDER_DEFAULT_VARIANT", "v2")

# ─── Neo4j Knowledge Graph ───────────────────────────────────────────────────
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "techstore123")
NEO4J_ENABLED = os.environ.get("NEO4J_ENABLED", "True").lower() in ("true", "1", "yes")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
