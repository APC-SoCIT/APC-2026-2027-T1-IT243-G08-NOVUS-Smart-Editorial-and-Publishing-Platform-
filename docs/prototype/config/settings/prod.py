import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Render sets RENDER_EXTERNAL_HOSTNAME automatically.
ALLOWED_HOSTS = [".onrender.com"]
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)

# The Vercel frontend calls this API cross-origin in production (there is no
# Vite proxy outside dev), so its origin must be allowed explicitly.
CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o
]
CSRF_TRUSTED_ORIGINS = [*CORS_ALLOWED_ORIGINS, "https://*.onrender.com"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
