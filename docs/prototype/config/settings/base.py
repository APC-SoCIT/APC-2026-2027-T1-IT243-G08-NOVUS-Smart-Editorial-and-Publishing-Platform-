from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

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
    "apps.common",
    "apps.accounts",
    "apps.editorial",
    "apps.ai_eval",
    "apps.publishing",
    "apps.content",
    "apps.design",
    "apps.issues",
    "apps.messaging",
    "apps.notifications",
    "apps.payments",
    "apps.reports",
    "apps.platform",
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
    "apps.platform.middleware.MaintenanceModeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"



AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_EVAL_MODEL = env("ANTHROPIC_EVAL_MODEL", default="claude-haiku-4-5-20251001")


import os
import dj_database_url

if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.parse(
            os.environ["DATABASE_URL"], conn_max_age=600, ssl_require=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# UC-1.5 pre-screening gate. A submission scoring below this is returned to the
# Writer with the AI's suggestions as revision notes; at or above it, the
# article reaches the Editor's queue. Business rule, not a technical constant --
# an Editor can still override the verdict under UC-1.8.
AI_PASSING_SCORE = 70

# UC-1.12: magazine design assets. Local storage in Phase 1; the container
# diagram specifies Cloudflare R2 for production.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# Declaring STORAGES anywhere replaces Django's defaults wholesale, so the
# "default" backend must be named explicitly or FileField uploads fail
# (UC-1.12 Upload Magazine Design).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Return relative media URLs ("/media/...") rather than absolute ones. The
# frontend is served from a different origin in development (Vite) and in
# production (Vercel), so an absolute backend URL is never the right one.
UPLOADED_FILES_USE_URL = False

# Shared secret for external schedulers. A cron service cannot hold a
# session, so scheduled endpoints authenticate with this instead.
SCHEDULER_TOKEN = os.environ.get("SCHEDULER_TOKEN", "")


# ---------------------------------------------------------------------------
# Object storage
#
# R2 is S3-compatible, so django-storages' S3 backend works unmodified — which
# is why the architecture could specify R2 without a custom storage layer.
#
# Falls back to local disk when unconfigured, so a checkout without credentials
# still runs. The fallback is development-only: a deployed instance writing to
# local disk loses every upload on redeploy.
# ---------------------------------------------------------------------------

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")

USE_R2 = all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
              R2_BUCKET_NAME])

if USE_R2:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": R2_BUCKET_NAME,
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "endpoint_url": f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            "region_name": "auto",
            # R2 does not implement ACLs; sending one is rejected.
            "default_acl": None,
            "querystring_auth": False,
            "custom_domain": R2_PUBLIC_URL.replace("https://", "").replace("http://", ""),
            # Keep both copies rather than overwriting: two writers uploading
            # the same filename should not silently replace each other's work.
            "file_overwrite": False,
            "signature_version": "s3v4",
        },
    }
