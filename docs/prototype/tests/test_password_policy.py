"""Password policy: every password is recorded, the last four cannot be
reused (PCI DSS 8.3.7), and a password expires after 90 days (8.3.9).

These sign in through the real token endpoint rather than forcing
authentication, because expiry is enforced where tokens are checked."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import PasswordHistory, User


def signin(client, email, password="pass1234"):
    r = client.post("/api/auth/token/", {"email": email, "password": password})
    assert r.status_code == 200, r.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return client


def change(client, current, new):
    return client.post("/api/auth/password/",
                       {"current_password": current, "new_password": new}, format="json")


@pytest.mark.django_db
class TestPasswordPolicy:
    def test_every_password_is_recorded(self, make_user):
        u = make_user("hist@boss.ph", User.Role.WRITER)
        assert u.password_history.count() == 1
        assert u.password_changed_at is not None

    def test_a_change_needs_the_current_password(self, api_client, make_user):
        make_user("cur@boss.ph", User.Role.WRITER)
        r = change(signin(api_client, "cur@boss.ph"), "wrong-one", "Brand-new-pass-91")
        assert r.status_code == 400 and "current_password" in r.data

    def test_the_last_four_passwords_cannot_be_reused(self, api_client, make_user):
        u = make_user("reuse@boss.ph", User.Role.WRITER)
        u.set_password("Original-pass-10")
        u.save()
        c = signin(api_client, "reuse@boss.ph", "Original-pass-10")
        seq = ["Original-pass-10", "Second-pass-21", "Third-pass-32", "Fourth-pass-43", "Fifth-pass-54"]
        for old, new in zip(seq, seq[1:]):
            assert change(c, old, new).status_code == 200
        r = change(c, "Fifth-pass-54", "Second-pass-21")      # four back: refused
        assert r.status_code == 400 and "new_password" in r.data
        r = change(c, "Fifth-pass-54", "Fifth-pass-54")       # the current one: refused
        assert r.status_code == 400
        assert change(c, "Fifth-pass-54", "Original-pass-10").status_code == 200   # five back

    def test_an_expired_password_locks_everything_except_changing_it(self, api_client, make_user):
        u = make_user("old@boss.ph", User.Role.WRITER)
        User.objects.filter(pk=u.pk).update(password_changed_at=timezone.now() - timedelta(days=91))
        c = signin(api_client, "old@boss.ph")
        r = c.get("/api/editorial/articles/")
        assert r.status_code == 403 and r.data["code"] == "password_change_required"
        me = c.get("/api/auth/me/")
        assert me.status_code == 200 and me.data["must_change_password"] is True
        assert User.objects.get(pk=u.pk).must_reset_password is True
        r = change(c, "pass1234", "Fresh-start-77")
        assert r.status_code == 200 and r.data["must_change_password"] is False
        assert c.get("/api/editorial/articles/").status_code == 200

    def test_an_administrator_can_require_a_change(self, api_client, make_user):
        u = make_user("forced@boss.ph", User.Role.EDITOR)
        User.objects.filter(pk=u.pk).update(must_reset_password=True)
        c = signin(api_client, "forced@boss.ph")
        assert c.get("/api/editorial/articles/").status_code == 403
        assert change(c, "pass1234", "Chosen-again-55").status_code == 200
        assert c.get("/api/editorial/articles/").status_code == 200

    def test_history_older_than_a_year_is_pruned_but_four_are_kept(self, make_user):
        u = make_user("prune@boss.ph", User.Role.WRITER)
        for i in range(6):
            u.set_password(f"Rotating-pass-{i}-xq")
            u.save()
        PasswordHistory.objects.filter(user=u).update(created_at=timezone.now() - timedelta(days=400))
        u.set_password("Latest-pass-99")
        u.save()
        assert u.password_history.count() == 4
