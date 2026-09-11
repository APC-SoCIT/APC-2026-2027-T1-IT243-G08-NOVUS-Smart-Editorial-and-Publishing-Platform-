from rest_framework.permissions import BasePermission


class IsRole(BasePermission):
    """Base class — don't use directly, use role_permission(...) below."""

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user

        if not (user and user.is_authenticated):
            return False

        # A suspended account is refused before any role is considered
        # (UC-5.2.2): suspension must revoke access immediately, whatever
        # authority the account otherwise holds.
        if getattr(user, "is_suspended", False):
            return False

        # An administrator is not a seventh workflow role — they hold every
        # role's authority. Without this an admin could configure the platform
        # but not operate it, which is not what the role means.
        if user.is_superuser or user.role == "ADMIN":
            return True

        return user.role in self.allowed_roles


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
