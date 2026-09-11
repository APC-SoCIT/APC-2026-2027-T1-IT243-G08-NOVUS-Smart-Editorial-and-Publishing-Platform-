import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Render supplies this at runtime; the wildcard covers the preview URLs.
ALLOWED_HOSTS = [".onrender.com"]
_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _host:
    ALLOWED_HOSTS.append(_host)

# In production the frontend is served from Vercel, a different origin — there
# is no Vite proxy to hide behind, so its URL must be allowed explicitly.
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
CSRF_TRUSTED_ORIGINS = [*CORS_ALLOWED_ORIGINS, "https://*.onrender.com"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
