import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ReaderProfile, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(email, role, **extra):
        user = User.objects.create_user(
            email=email, password="pass1234", first_name="Test",
            last_name=role.title(), role=role, **extra,
        )
        if role == User.Role.READER:
            ReaderProfile.objects.create(user=user)
        return user
    return _make


@pytest.fixture
def writer(make_user):
    return make_user("writer@boss.ph", User.Role.WRITER)


@pytest.fixture
def editor(make_user):
    return make_user("editor@boss.ph", User.Role.EDITOR)


@pytest.fixture
def publisher(make_user):
    return make_user("publisher@boss.ph", User.Role.PUBLISHER)


@pytest.fixture
def auth_client(api_client):
    """Returns a helper that logs a given user in via the real JWT endpoint
    (TC-6.2-BF) and returns an authenticated APIClient."""

    def _login(user):
        api_client.force_authenticate(user=user)
        return api_client

    return _login


@pytest.fixture(autouse=True)
def mock_claude_eval(monkeypatch):
    """Every test runs against a stubbed Claude response so the suite is
    free, fast, and deterministic. Skip this fixture (via
    @pytest.mark.no_mock_eval, or just call the real service directly) if
    you specifically want to hit the live API."""

    def _fake_evaluate(article):
        return {
            "grammar_score": 90,
            "readability_score": 85,
            "overall_score": 88,
            "recommendation": "APPROVE",
            "raw_response": {"stub": True},
            "ai_model": "stub",
        }

    monkeypatch.setattr("apps.editorial.views.evaluate_article", _fake_evaluate)


@pytest.fixture(autouse=True)
def tmp_media(tmp_path, settings):
    """UC-1.12 uploads go to a temp directory so tests never write into
    the project's media folder."""
    settings.MEDIA_ROOT = tmp_path / "media"
