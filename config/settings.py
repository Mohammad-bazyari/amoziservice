"""
Django settings for استا سرویس.

Everything deployment-specific (SECRET_KEY, DEBUG, ALLOWED_HOSTS, database
URL, Kavenegar credentials, trusted origins) is read from environment
variables so the same code works locally (SQLite) and on cPanel (MySQL).
"""
import os
from pathlib import Path

try:
    import dj_database_url
except ImportError:  # pragma: no cover
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: str = "False") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


# SECURITY WARNING: keep the secret key out of version control.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")

# SECURITY WARNING: don't run with debug turned on in production.
DEBUG = env_bool("DJANGO_DEBUG", "True")

hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in hosts.split(",") if h.strip()]

csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins.split(",") if o.strip()]

# Application definition
INSTALLED_APPS = [
    # Local apps
    "apps.core.apps.CoreConfig",
    "apps.content.apps.ContentConfig",
    "apps.brands.apps.BrandsConfig",
    "apps.services.apps.ServicesConfig",
    "apps.requests.apps.RequestsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.accounts.apps.AccountsConfig",
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Project context processors
                "apps.core.context_processors.site_settings",
                "apps.core.context_processors.default_service",
                "apps.core.context_processors.footer_areas",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Auth
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"

# Database
# Local default: SQLite. On cPanel set DATABASE_URL, e.g.
# mysql://cpaneluser_dbuser:password@localhost:3306/cpaneluser_dbname
if dj_database_url is not None and os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization — Persian UI with Jalali dates in admin dashboards
LANGUAGE_CODE = "fa"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Tehran")
USE_I18N = True
USE_TZ = True
# Persian locale formats render Latin digits with fa separators; we render
# Persian digits ourselves via the fa_digits filter where needed.
FORMAT_MODULE_PATH = None

# Icons offered in the admin icon picker for services (must match bundled
# names in static/js/lucide-icons.js).
ADMIN_ICON_CHOICES = (
    "flame",        # پکیج / گرمایش
    "droplets",     # آب / تصفیه
    "wrench",       # تعمیر عمومی
    "zap",          # برقی
    "gauge",        # تنظیم فشار
    "timer",        # سرویس دوره‌ای
    "shield-check", # گارانتی
    "clipboard-check",
    "phone-call",
    "search-check",
    "target",
)

# Static files (CSS, JavaScript, Images) — served by WhiteNoise in prod
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media (customer uploads, CMS images)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Upload hardening for customer-submitted images
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB total POST body
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # keep small files in memory
REQUEST_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # per-image limit used by the form
REQUEST_IMAGE_MAX_COUNT = 3  # max images per request

# SMS — Kavenegar (https://kavenegar.com/rest.html)
# The API key is server-side only and never rendered into any template.
KAVENEGAR_API_KEY = os.environ.get("KAVENEGAR_API_KEY", "")
KAVENEGAR_SENDER = os.environ.get("KAVENEGAR_SENDER", "")
# Local default is False: a mock provider is used and no paid SMS is sent.
KAVENEGAR_ENABLED = env_bool("KAVENEGAR_ENABLED", "False")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Admin panel branding
ADMIN_SITE_HEADER = "استا سرویس — پنل مدیریت"

# Production hardening (harmless when DEBUG=True locally)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", "True")
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_HTTPONLY = True

# Logging to file (shared-hosting friendly; no syslog dependency)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "maxBytes": 2 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["file"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["file"], "level": "ERROR", "propagate": False},
        "apps.notifications": {"handlers": ["file"], "level": "INFO", "propagate": False},
    },
}
