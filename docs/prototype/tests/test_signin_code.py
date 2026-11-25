"""Sign-in verification code (adviser meeting, Nov 24): a correct password
is not enough for staff; the emailed code finishes the sign-in."""
import pytest
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import SignInChallenge, User
from tests.conftest import code_from_outbox

TOKEN, CODE, RESEND = "/api/auth/token/", "/api/auth/token/code/", "/api/auth/token/resend/"


def password(email, pw="pass1234"):
    return APIClient().post(TOKEN, {"email": email, "password": pw})


def code(challenge, value):
    return APIClient().post(CODE, {"challenge": challenge, "code": value})


@pytest.mark.django_db
class TestStaffNeedACode:
    def test_the_password_alone_gives_no_tokens(self, editor):
        r = password("editor@boss.ph")
        assert r.status_code == 202
        assert "access" not in r.data and r.data["code_required"] is True
        assert r.data["sent_to"] == "e*****@boss.ph"
        assert len(mail.outbox) == 1 and "sign-in code" in mail.outbox[0].subject.lower()

    def test_the_right_code_signs_in(self, editor):
        r = password("editor@boss.ph")
        t = code(r.data["challenge"], code_from_outbox())
        assert t.status_code == 200 and t.data["access"] and t.data["refresh"]
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {t.data['access']}")
        assert c.get("/api/auth/me/").data["email"] == "editor@boss.ph"

    def test_a_code_works_once(self, editor):
        r = password("editor@boss.ph")
        right = code_from_outbox()
        assert code(r.data["challenge"], right).status_code == 200
        assert code(r.data["challenge"], right).data["code"] == "code_expired"

    def test_five_wrong_codes_end_it(self, editor):
        r = password("editor@boss.ph")
        right = code_from_outbox()
        wrong = "000000" if right != "000000" else "111111"
        for left in (4, 3, 2, 1):
            assert code(r.data["challenge"], wrong).data["attempts_left"] == left
        assert code(r.data["challenge"], wrong).data["code"] == "too_many_attempts"
        assert code(r.data["challenge"], right).data["code"] == "code_expired"

    def test_a_wrong_password_sends_nothing(self, editor):
        assert password("editor@boss.ph", "wrong").status_code == 401
        assert not mail.outbox

    def test_the_code_is_not_stored_as_sent(self, editor):
        r = password("editor@boss.ph")
        ch = SignInChallenge.objects.get()
        assert code_from_outbox() not in ch.code_hmac
        assert r.data["challenge"] != ch.challenge_hash

    def test_a_new_sign_in_retires_the_old_challenge(self, editor):
        first = password("editor@boss.ph").data["challenge"]
        old_code = code_from_outbox()
        password("editor@boss.ph")
        assert code(first, old_code).data["code"] == "code_expired"

    def test_suspended_between_the_steps(self, editor):
        r = password("editor@boss.ph")
        User.objects.filter(pk=editor.pk).update(is_suspended=True, is_active=False)
        assert code(r.data["challenge"], code_from_outbox()).status_code == 400


@pytest.mark.django_db
class TestResend:
    def test_too_soon_then_a_new_code(self, editor, monkeypatch):
        r = password("editor@boss.ph")
        first = code_from_outbox()
        assert APIClient().post(RESEND, {"challenge": r.data["challenge"]}).status_code == 429
        from apps.accounts import signin
        monkeypatch.setattr(signin, "RESEND_WAIT", signin.timedelta(0))
        again = APIClient().post(RESEND, {"challenge": r.data["challenge"]})
        assert again.status_code == 200 and len(mail.outbox) == 2
        second = code_from_outbox()
        if first != second:
            assert code(r.data["challenge"], first).data["code"] == "wrong_code"
        assert code(r.data["challenge"], second).status_code == 200

    def test_at_most_three_sends(self, editor, monkeypatch):
        from apps.accounts import signin
        monkeypatch.setattr(signin, "RESEND_WAIT", signin.timedelta(0))
        r = password("editor@boss.ph")
        for _ in range(2):
            assert APIClient().post(RESEND, {"challenge": r.data["challenge"]}).status_code == 200
        last = APIClient().post(RESEND, {"challenge": r.data["challenge"]})
        assert last.data["code"] == "too_many_sends"


@pytest.mark.django_db
class TestReaders:
    def test_a_reader_signs_in_with_the_password_alone(self, make_user):
        make_user("r@boss.ph", User.Role.READER)
        r = password("r@boss.ph")
        assert r.status_code == 200 and "access" in r.data

    def test_a_reader_can_turn_codes_on(self, make_user, sign_in):
        make_user("r@boss.ph", User.Role.READER)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {sign_in('r@boss.ph')['access']}")
        assert c.patch("/api/auth/me/", {"signin_code_enabled": True}, format="json").status_code == 200
        assert password("r@boss.ph").status_code == 202

    def test_staff_cannot_turn_codes_off(self, editor, sign_in):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {sign_in('editor@boss.ph')['access']}")
        c.patch("/api/auth/me/", {"signin_code_enabled": False}, format="json")
        assert password("editor@boss.ph").status_code == 202


@pytest.mark.django_db
@override_settings(SIGNIN_CODE_REQUIRED=False)
def test_a_practice_server_can_switch_codes_off(editor):
    assert password("editor@boss.ph").status_code == 200
