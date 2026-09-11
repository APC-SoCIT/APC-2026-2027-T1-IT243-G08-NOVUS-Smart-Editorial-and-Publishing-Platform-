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
# Vercel gives every deployment its own hostname, so a fixed allow-list
# only ever covers the production alias. The pattern below admits this
# project's preview builds as well, which is what makes testing a branch
# against the live API possible.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://novusdeploy.*\.vercel\.app$",
]

CSRF_TRUSTED_ORIGINS = [
    *CORS_ALLOWED_ORIGINS,
    "https://*.onrender.com",
    "https://*.vercel.app",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
