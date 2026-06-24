import os
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-only-change-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "apps.accounts",
    "apps.marketplace",
    "apps.logistics",
    "apps.payments",
    "apps.ai_services",
    "apps.disputes",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="agripay"),
        "USER": config("DB_USER", default="agripay"),
        "PASSWORD": config("DB_PASSWORD", default="agripay"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

if config("USE_SQLITE", default=False, cast=bool):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
else:
    _db_url = config("DATABASE_URL", default="")
    if _db_url:
        import dj_database_url

        DATABASES["default"] = dj_database_url.parse(_db_url, conn_max_age=600)

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

_dev_cors_origins = [
    "http://127.0.0.1:5174",
    "http://localhost:5174",
]
_configured_cors = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())
if DEBUG:
    CORS_ALLOWED_ORIGINS = list(dict.fromkeys(_dev_cors_origins + list(_configured_cors)))
elif _configured_cors:
    CORS_ALLOWED_ORIGINS = _configured_cors
else:
    CORS_ALLOWED_ORIGINS = _dev_cors_origins
CORS_ALLOW_CREDENTIALS = True

# East Africa country config
SUPPORTED_COUNTRIES = {
    "UG": {"name": "Uganda", "currency": "UGX", "phone_prefix": "+256"},
    "KE": {"name": "Kenya", "currency": "KES", "phone_prefix": "+254"},
    "TZ": {"name": "Tanzania", "currency": "TZS", "phone_prefix": "+255"},
    "RW": {"name": "Rwanda", "currency": "RWF", "phone_prefix": "+250"},
}

# Mobile money sandbox
MTN_MOMO_API_USER = config("MTN_MOMO_API_USER", default="")
MTN_MOMO_API_KEY = config("MTN_MOMO_API_KEY", default="")
MTN_MOMO_SUBSCRIPTION_KEY = config("MTN_MOMO_SUBSCRIPTION_KEY", default="")
MTN_MOMO_ENV = config("MTN_MOMO_ENV", default="sandbox")
AIRTEL_MONEY_CLIENT_ID = config("AIRTEL_MONEY_CLIENT_ID", default="")
AIRTEL_MONEY_CLIENT_SECRET = config("AIRTEL_MONEY_CLIENT_SECRET", default="")

# Stripe
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
