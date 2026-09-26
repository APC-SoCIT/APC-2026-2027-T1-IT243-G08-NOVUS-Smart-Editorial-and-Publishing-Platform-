"""
Rate limits on the endpoints that accept a password or create an account.

Sign-in is limited per account rather than per address. Behind the hosting
provider's proxies the caller's address arrives in a forwarding header the
caller can partly control, so a limit keyed on it can be dodged by varying
the header. The account under attack is the one thing an attacker cannot
vary. The cost is that a user can be locked out for up to a minute by
someone else's attempts, which is the usual trade.

Counts live in Django's cache. With a single application process that is
shared by every request; it resets when the service restarts.
"""
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        if not email:
            return None      # a malformed request, which the view rejects anyway
        return self.cache_format % {"scope": self.scope, "ident": email}


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class RefreshRateThrottle(AnonRateThrottle):
    scope = "refresh"
