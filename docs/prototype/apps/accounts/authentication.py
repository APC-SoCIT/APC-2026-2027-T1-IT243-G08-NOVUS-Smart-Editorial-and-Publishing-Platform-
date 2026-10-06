"""
Password expiry (PCI DSS 8.3.9), enforced where every API request is
authenticated.

A password older than the configured period sets must_reset_password, the
same flag an administrator sets to force a change. While it is set, the
account may read its own profile and change its password, and nothing else:
the check runs on the server, so it holds whatever the browser does.
"""
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

# What a locked account may still reach.
ALLOWED = ("/api/auth/me/", "/api/auth/password/", "/api/auth/token/", "/api/health/")


class PasswordPolicyAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, _token = result

        if user.password_expired and not user.must_reset_password:
            type(user).objects.filter(pk=user.pk).update(must_reset_password=True)
            user.must_reset_password = True

        if user.must_reset_password and not request.path.startswith(ALLOWED):
            raise PermissionDenied({
                "detail": "Your password must be changed before you continue.",
                "code": "password_change_required",
            })
        return result
