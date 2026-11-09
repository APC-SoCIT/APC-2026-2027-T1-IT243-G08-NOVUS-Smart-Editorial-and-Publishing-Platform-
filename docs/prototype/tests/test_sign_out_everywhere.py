"""UC-5.2.2: a password reset signs the account out on every device.
 
These use the real sign-in endpoint, since the point is what happens to
tokens already handed out."""
import pytest
from rest_framework.test import APIClient
 
from apps.accounts.models import PasswordResetToken, User
 
NEW = "N3w-Passphrase!"
 
 
def sign_in(email, password):
    r = APIClient().post("/api/auth/token/", {"email": email, "password": password})
    assert r.status_code == 200, r.data
    return r.data
 
 
def me(access):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return c.get("/api/auth/me/")
 
 
def refresh(token):
    return APIClient().post("/api/auth/token/refresh/", {"refresh": token})
 
 
def reset_password(user, new=NEW):
    raw = PasswordResetToken.issue(user, ip="127.0.0.1")
    r = APIClient().post("/api/auth/password/reset/", {"token": raw, "new_password": new})
    assert r.status_code == 200, r.data
 
 
@pytest.mark.django_db
class TestSignOutEverywhere:
    def test_a_reset_ends_every_existing_session(self, make_user):     # TC-5.2.2-BF
        user = make_user("reader@boss.ph", User.Role.READER)
        laptop, phone = sign_in(user.email, "pass1234"), sign_in(user.email, "pass1234")
        assert me(laptop["access"]).status_code == 200
 
        reset_password(user)
 
        for device in (laptop, phone):
            assert me(device["access"]).status_code == 401
            assert refresh(device["refresh"]).status_code == 401
 
    def test_signing_in_with_the_new_password_works(self, make_user):
        user = make_user("reader@boss.ph", User.Role.READER)
        sign_in(user.email, "pass1234")
        reset_password(user)
        fresh = sign_in(user.email, NEW)
        assert me(fresh["access"]).status_code == 200
        rotated = refresh(fresh["refresh"])
        assert rotated.status_code == 200
        assert me(rotated.data["access"]).status_code == 200
 
    def test_a_normal_session_is_untouched(self, make_user):
        user = make_user("writer@boss.ph", User.Role.WRITER)
        s = sign_in(user.email, "pass1234")
        r = refresh(s["refresh"])
        assert r.status_code == 200 and me(r.data["access"]).status_code == 200
 
    def test_tokens_from_before_the_change_still_work(self, make_user):
        # Tokens issued before deployment carry no session claim. Reading
        # the missing claim as 0 means deploying this signs nobody out.
        from rest_framework_simplejwt.tokens import RefreshToken
        user = make_user("editor@boss.ph", User.Role.EDITOR)
        old = RefreshToken.for_user(user)
        assert "sv" not in old
        assert me(str(old.access_token)).status_code == 200
        assert refresh(str(old)).status_code == 200
 
    def test_a_deactivated_account_cannot_refresh(self, make_user):
        user = make_user("reader@boss.ph", User.Role.READER)
        s = sign_in(user.email, "pass1234")
        User.objects.filter(pk=user.pk).update(is_active=False)
        assert refresh(s["refresh"]).status_code == 401
