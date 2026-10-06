"""
Password reuse rule (PCI DSS 8.3.7): a new password may not match any of the
account's last few passwords. Runs with Django's other password validators,
so it applies wherever a password is set through validate_password.
"""
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError


class PasswordHistoryValidator:
    def __init__(self, count=None):
        self.count = count

    def _count(self):
        return self.count or getattr(settings, "PASSWORD_HISTORY_COUNT", 4)

    def validate(self, password, user=None):
        if user is None or not getattr(user, "pk", None):
            return  # a new account has no history to repeat
        recent = user.password_history.order_by("-created_at", "-id")[: self._count()]
        for entry in recent:
            if check_password(password, entry.password_hash):
                raise ValidationError(
                    f"You have used this password recently. Choose one that is not "
                    f"among your last {self._count()} passwords.",
                    code="password_reused")

    def get_help_text(self):
        return f"Your password cannot match any of your last {self._count()} passwords."
