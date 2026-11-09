"""UC-5.2.2 Recover a Forgotten Password (FR-ACC-02b, NFR-12).

Emails go to Django's in-memory outbox during tests, so these check what a
user would actually receive."""
import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import PasswordResetToken, User
from apps.notifications.models import EmailDispatch

SENT = "If an account uses that address, we've sent a reset link."


def forgot(client, email):
    return client.post("/api/auth/password/forgot/", {"email": email}, format="json")


def reset(client, token, password):
    return client.post("/api/auth/password/reset/", {"token": token, "new_password": password}, format="json")


def link_token():
    """The token from the reset link in the last email sent."""
    return re.search(r"reset-password\?token=([\w-]+)", mail.outbox[-1].body).group(1)


@pytest.fixture(autouse=True)
def clear_throttles():
    from django.core.cache import cache
    cache.clear()


@pytest.mark.django_db
class TestPasswordRecovery:
    def test_same_answer_for_every_address(self, api_client, make_user):      # TC-5.2.2-A1
        make_user("known@boss.ph", User.Role.READER)
        a, b = forgot(api_client, "known@boss.ph"), forgot(api_client, "nobody@boss.ph")
        assert a.status_code == b.status_code == 200
        assert a.data == b.data == {"detail": SENT}
        assert len(mail.outbox) == 1 and mail.outbox[0].to == ["known@boss.ph"]

    def test_link_is_emailed_and_stored_only_as_a_hash(self, api_client, make_user):   # TC-5.2.2-BF
        u = make_user("hash@boss.ph", User.Role.WRITER)
        forgot(api_client, "HASH@boss.ph")          # any letter case finds the account
        raw = link_token()
        token = PasswordResetToken.objects.get(user=u)
        assert token.token_hash != raw and token.token_hash == PasswordResetToken.hash(raw)
        assert timedelta(minutes=59) < token.expires_at - timezone.now() <= timedelta(minutes=60)
        dispatch = EmailDispatch.objects.get(recipient=u)
        assert dispatch.status == EmailDispatch.Status.SENT and dispatch.template == "password_reset"
        assert "<a href=" in mail.outbox[0].alternatives[0][0]

    def test_reset_sets_the_password_and_spends_the_link(self, api_client, make_user):  # TC-5.2.2-BF
        u = make_user("reset@boss.ph", User.Role.WRITER, must_reset_password=True)
        forgot(api_client, "reset@boss.ph")
        raw = link_token()
        assert api_client.post("/api/auth/password/reset/verify/", {"token": raw}, format="json").status_code == 200
        r = reset(api_client, raw, "Fresh-start-pass-77")
        assert r.status_code == 200 and r.data["staff"] is True
        u.refresh_from_db()
        assert u.check_password("Fresh-start-pass-77") and not u.must_reset_password
        assert u.password_history.count() == 2
        again = reset(api_client, raw, "Another-pass-88")
        assert again.status_code == 400 and again.data["code"] == "invalid_link"
        signin = api_client.post("/api/auth/token/", {"email": "reset@boss.ph", "password": "Fresh-start-pass-77"})
        assert signin.status_code == 200

    def test_expired_link_is_refused(self, api_client, make_user):           # TC-5.2.2-E1
        make_user("late@boss.ph", User.Role.READER)
        forgot(api_client, "late@boss.ph")
        raw = link_token()
        PasswordResetToken.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        r = api_client.post("/api/auth/password/reset/verify/", {"token": raw}, format="json")
        assert r.status_code == 400 and r.data["code"] == "invalid_link"
        assert reset(api_client, raw, "Fresh-start-pass-77").status_code == 400

    def test_a_new_request_retires_the_older_link(self, api_client, make_user):
        make_user("twice@boss.ph", User.Role.READER)
        forgot(api_client, "twice@boss.ph"); first = link_token()
        forgot(api_client, "twice@boss.ph"); second = link_token()
        assert reset(api_client, first, "Fresh-start-pass-77").status_code == 400
        assert reset(api_client, second, "Fresh-start-pass-77").status_code == 200

    def test_recent_and_weak_passwords_are_refused(self, api_client, make_user):   # TC-5.2.2-E2
        make_user("rules@boss.ph", User.Role.READER)          # current password is pass1234
        forgot(api_client, "rules@boss.ph")
        raw = link_token()
        r = reset(api_client, raw, "pass1234")
        assert r.status_code == 400 and "new_password" in r.data
        assert reset(api_client, raw, "12345678").status_code == 400
        assert reset(api_client, raw, "Fresh-start-pass-77").status_code == 200   # link still usable

    def test_suspended_account_gets_no_email(self, api_client, make_user):
        make_user("held@boss.ph", User.Role.WRITER, is_suspended=True)
        assert forgot(api_client, "held@boss.ph").data == {"detail": SENT}
        assert mail.outbox == []

    def test_requests_are_limited_per_address(self, api_client, make_user):
        make_user("flood@boss.ph", User.Role.READER)
        codes = [forgot(api_client, "flood@boss.ph").status_code for _ in range(6)]
        assert codes[:5] == [200] * 5 and codes[5] == 429
        assert len(mail.outbox) == 5

    def test_a_failed_send_is_recorded_not_raised(self, api_client, make_user, settings):
        settings.EMAIL_BACKEND = "apps.notifications.backends.ResendEmailBackend"
        settings.RESEND_API_KEY = "re_invalid"
        import httpx
        def boom(*a, **k):
            raise httpx.ConnectError("no network")
        import apps.notifications.backends as b
        orig = b.httpx.Client.post
        b.httpx.Client.post = boom
        try:
            u = make_user("down@boss.ph", User.Role.READER)
            assert forgot(api_client, "down@boss.ph").status_code == 200
        finally:
            b.httpx.Client.post = orig
        d = EmailDispatch.objects.get(recipient=u)
        assert d.status == EmailDispatch.Status.FAILED and "no network" in d.last_error
