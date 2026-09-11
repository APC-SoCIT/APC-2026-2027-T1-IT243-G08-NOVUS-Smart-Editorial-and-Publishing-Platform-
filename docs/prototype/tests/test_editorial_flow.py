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


@pytest.mark.django_db
class TestAIPreScreeningGate:
    """UC-1.5: submissions below the passing score are returned to the Writer
    with the AI's suggestions as revision notes; the Editor can still see them."""

    def _draft(self, client):
        r = client.post("/api/editorial/articles/", {
            "title": "Gate Test", "body": "Body text " * 50, "category": "Tech"})
        return r.data["id"]

    def test_passing_score_reaches_the_editor(self, auth_client, writer, monkeypatch):
        monkeypatch.setattr("apps.editorial.views.evaluate_article", lambda a: {
            "grammar_score": 90, "readability_score": 85, "overall_score": 88,
            "recommendation": "APPROVE", "summary": "Solid.", "suggestions": [],
            "raw_response": {}, "ai_model": "stub"})
        client = auth_client(writer)
        aid = self._draft(client)
        r = client.post(f"/api/editorial/articles/{aid}/submit/")
        assert r.data["gate"] == "PASSED"
        assert Article.objects.get(id=aid).status == Article.Status.UNDER_REVIEW

    def test_failing_score_returns_to_writer_with_notes(self, auth_client, writer, monkeypatch):
        monkeypatch.setattr("apps.editorial.views.evaluate_article", lambda a: {
            "grammar_score": 50, "readability_score": 55, "overall_score": 52,
            "recommendation": "REJECT", "summary": "Needs work.",
            "suggestions": [{"section": "Intro", "note_type": "STRUCTURE",
                             "instruction": "Lead with the main claim.",
                             "priority": "HIGH"}],
            "raw_response": {}, "ai_model": "stub"})
        client = auth_client(writer)
        aid = self._draft(client)
        r = client.post(f"/api/editorial/articles/{aid}/submit/")
        assert r.data["gate"] == "RETURNED"

        article = Article.objects.get(id=aid)
        assert article.status == Article.Status.REVISION_REQUESTED
        notes = article.revision_notes.filter(editor__isnull=True)
        assert notes.count() == 1
        assert notes.first().priority == "HIGH"

    def test_editor_can_still_see_an_ai_returned_article(
        self, auth_client, writer, editor, monkeypatch
    ):
        monkeypatch.setattr("apps.editorial.views.evaluate_article", lambda a: {
            "grammar_score": 40, "readability_score": 40, "overall_score": 40,
            "recommendation": "REJECT", "summary": "", "suggestions": [],
            "raw_response": {}, "ai_model": "stub"})
        wc = auth_client(writer)
        aid = self._draft(wc)
        wc.post(f"/api/editorial/articles/{aid}/submit/")

        ec = auth_client(editor)
        listed = ec.get("/api/editorial/articles/")
        match = [a for a in listed.data["results"] if a["id"] == aid]
        assert match, "Editor must be able to see AI-returned articles"
        assert match[0]["returned_by_ai"] is True


@pytest.mark.django_db
class TestMagazineDesignFlow:
    """UC-1.12 through UC-1.15: upload, review, revise, resubmit."""

    def _issue(self, publisher, number=12):
        from apps.issues.models import Issue
        return Issue.objects.create(number=number, title="Test Issue",
                                    created_by=publisher)

    def _upload(self, client, issue, version="v1.0"):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("layout.pdf", b"%PDF-1.4 fake",
                               content_type="application/pdf")
        return client.post("/api/design/designs/",
                           {"issue": issue.id, "version": version, "file": f,
                            "notes_to_editor": "First pass."},
                           format="multipart")

    def test_designer_uploads_and_editor_approves(
        self, auth_client, make_user, editor, publisher
    ):
        from apps.accounts.models import User
        designer = make_user("designer@boss.ph", User.Role.GRAPHIC_DESIGNER)
        issue = self._issue(publisher)

        r = self._upload(auth_client(designer), issue)
        assert r.status_code == status.HTTP_201_CREATED
        assert r.data["status"] == "PENDING_REVIEW"

        did = r.data["id"]
        approved = auth_client(editor).post(f"/api/design/designs/{did}/approve/")
        assert approved.status_code == status.HTTP_200_OK
        assert approved.data["status"] == "APPROVED"

    def test_editor_requests_revision_and_designer_resubmits(
        self, auth_client, make_user, editor, publisher
    ):
        from apps.accounts.models import User
        from apps.design.models import MagazineDesign
        designer = make_user("designer2@boss.ph", User.Role.GRAPHIC_DESIGNER)
        issue = self._issue(publisher, number=13)

        did = self._upload(auth_client(designer), issue).data["id"]

        r = auth_client(editor).post(
            f"/api/design/designs/{did}/request-revision/",
            {"notes": "Cover typography is too tight."})
        assert r.data["status"] == "REVISION_REQUESTED"

        # UC-1.15: resubmission is a new version and the old one is superseded,
        # not overwritten, so the review history survives.
        again = self._upload(auth_client(designer), issue, version="v1.1")
        assert again.status_code == status.HTTP_201_CREATED
        assert MagazineDesign.objects.filter(issue=issue).count() == 2
        assert MagazineDesign.objects.get(pk=did).status == "SUPERSEDED"

    def test_rejects_unsupported_file_type(self, auth_client, make_user, publisher):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.accounts.models import User
        designer = make_user("designer3@boss.ph", User.Role.GRAPHIC_DESIGNER)
        issue = self._issue(publisher, number=14)

        f = SimpleUploadedFile("notes.exe", b"nope",
                               content_type="application/octet-stream")
        r = auth_client(designer).post("/api/design/designs/",
            {"issue": issue.id, "version": "v1.0", "file": f}, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDesignerArticleAccess:
    """UC-1.12: the Designer reads finalised copy, not the whole pipeline."""

    def test_designer_sees_only_approved_and_published(
        self, auth_client, make_user, writer
    ):
        from apps.accounts.models import User
        designer = make_user("designer4@boss.ph", User.Role.GRAPHIC_DESIGNER)

        approved = Article.objects.create(
            writer=writer, title="Ready", body="<p>Final copy.</p>",
            category="Tech", status=Article.Status.APPROVED)
        draft = Article.objects.create(
            writer=writer, title="Not ready", body="<p>Notes.</p>",
            category="Tech", status=Article.Status.DRAFTING)

        r = auth_client(designer).get("/api/editorial/articles/")
        ids = [a["id"] for a in r.data["results"]]
        assert approved.id in ids
        assert draft.id not in ids, "Designer must not see drafts"

    def test_designer_can_read_approved_article_body(
        self, auth_client, make_user, writer
    ):
        from apps.accounts.models import User
        designer = make_user("designer5@boss.ph", User.Role.GRAPHIC_DESIGNER)
        a = Article.objects.create(
            writer=writer, title="Layout me", body="<p>Body for layout.</p>",
            category="Life", status=Article.Status.APPROVED)

        r = auth_client(designer).get(f"/api/editorial/articles/{a.id}/")
        assert r.status_code == status.HTTP_200_OK
        assert "Body for layout" in r.data["body"]
