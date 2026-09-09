"""
Worked example: turns TC-6.2-BF (Verify Authenticate User) and TC-1.2-BF
(Verify Submit Article) — plus the rest of the Phase-1 chain through to
UC-7.1 — into pytest. Copy this file's shape for new use cases: one test
per BF (basic flow) test case first, exception flows (E-AUTH etc.) after,
rather than inventing a new test style per app.
"""
import pytest
from rest_framework import status

from apps.accounts.models import User
from apps.editorial.models import Article


@pytest.mark.django_db
class TestAuthenticateUser:
    def test_tc_6_2_bf_login_returns_access_and_refresh_tokens(self, api_client, writer):
        response = api_client.post(
            "/api/auth/token/", {"email": "writer@boss.ph", "password": "pass1234"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_e_auth_wrong_password_is_rejected(self, api_client, writer):
        response = api_client.post(
            "/api/auth/token/", {"email": "writer@boss.ph", "password": "wrong"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestEditorialPipelineEndToEnd:
    """Login -> Draft -> Submit (auto AI-eval) -> Editor Approve -> Publish
    -> Public read. Mirrors the Phase-1 scope in README exactly."""

    def test_tc_1_2_bf_writer_can_draft_and_submit_article(self, auth_client, writer):
        client = auth_client(writer)

        draft = client.post(
            "/api/editorial/articles/",
            {"title": "AI in Everyday Workspaces", "body": "Body text " * 50, "category": "Business"},
        )
        assert draft.status_code == status.HTTP_201_CREATED
        article_id = draft.data["id"]

        submitted = client.post(f"/api/editorial/articles/{article_id}/submit/")
        assert submitted.status_code == status.HTTP_201_CREATED
        assert submitted.data["overall_score"] == 88  # from the stubbed Claude response

        article = Article.objects.get(id=article_id)
        assert article.status == Article.Status.UNDER_REVIEW

    def test_full_flow_publishes_and_is_publicly_readable(
        self, api_client, auth_client, writer, editor, publisher
    ):
        writer_client = auth_client(writer)
        draft = writer_client.post(
            "/api/editorial/articles/",
            {"title": "Sustainable Tech in 2026", "body": "Body text " * 50, "category": "Tech"},
        )
        article_id = draft.data["id"]
        writer_client.post(f"/api/editorial/articles/{article_id}/submit/")

        editor_client = auth_client(editor)
        approved = editor_client.post(f"/api/editorial/articles/{article_id}/approve/")
        assert approved.status_code == status.HTTP_200_OK
        assert approved.data["status"] == "APPROVED"

        publisher_client = auth_client(publisher)
        published = publisher_client.post(f"/api/editorial/articles/{article_id}/publish/")
        assert published.status_code == status.HTTP_200_OK
        assert published.data["status"] == "PUBLISHED"

        # UC-7.1 Browse Featured Content — no auth required
        public = api_client.get("/api/content/articles/")
        assert public.status_code == status.HTTP_200_OK
        assert any(a["id"] == article_id for a in public.data["results"])

    def test_publish_before_approval_is_rejected(self, auth_client, writer, publisher):
        writer_client = auth_client(writer)
        draft = writer_client.post(
            "/api/editorial/articles/",
            {"title": "Not Ready Yet", "body": "Body text " * 50, "category": "Tech"},
        )
        article_id = draft.data["id"]

        publisher_client = auth_client(publisher)
        response = publisher_client.post(f"/api/editorial/articles/{article_id}/publish/")
        assert response.status_code == status.HTTP_409_CONFLICT
