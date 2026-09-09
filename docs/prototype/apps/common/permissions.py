from rest_framework.permissions import BasePermission


class IsRole(BasePermission):
    """Base class — don't use directly, use role_permission(...) below."""

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and not getattr(user, "is_suspended", False)
            and user.role in self.allowed_roles
        )


def role_permission(*roles):
    """
    Usage: permission_classes = [role_permission("EDITOR", "ADMIN")]

    Every protected, state-changing action in the test spec has an
    "E-AUTH" exception flow (session/permission failure -> blocked, no
    partial state change). DRF's permission check runs before the view
    body executes, so using this consistently is what makes those E-AUTH
    test cases pass for free.
    """
    return type("_RolePermission", (IsRole,), {"allowed_roles": roles})
