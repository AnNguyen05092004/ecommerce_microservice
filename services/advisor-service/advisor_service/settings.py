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
    # "advisor.middleware.AdvisorRateLimitMiddleware",  # Temporarily disabled for development
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

PRODUCT_SERVICE_URL = os.environ.get(
    "PRODUCT_SERVICE_URL", "http://product-service:8017"
)
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
