"""
A health check for uptime monitoring.

Reports whether the service can reach its database, and nothing else: no
version, no settings, no counts, since the endpoint is public and anything
it reveals is revealed to everyone. Excluded from rate limiting so a
monitor checking every few minutes is never refused.
"""
from django.db import connection
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET", "HEAD"])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        ok = True
    except Exception:
        ok = False
    r = Response({"status": "ok" if ok else "unavailable"}, status=200 if ok else 503)
    r["Cache-Control"] = "no-store"
    return r
