"""
Worked example: turns TC-6.2-BF (Verify Authenticate User) and TC-1.2-BF
(Verify Submit Article) — plus the rest of the Phase-1 chain through to
UC-7.1 — into pytest. Copy this file's shape for new use cases: one test
per BF (basic flow) test case first, exception flows (E-AUTH etc.) after,
rather than inventing a new test style per app.
"""
from django.utils import timezone
import pytest
from rest_framework import status


def _tiny_png():
    """A real 1x1 PNG. ImageField opens uploads with Pillow, so a fabricated
    header is rejected as a corrupt image."""
    import io
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(buf, format="PNG")
    return SimpleUploadedFile("cover.png", buf.getvalue(), content_type="image/png")

from apps.accounts.models import User
from apps.editorial.models import Article


def draft_copy(paragraphs=4):
    """Copy a writer would plausibly submit.

    The readiness checks refuse work that is obviously unfinished, so a
    fixture of repeated filler no longer stands in for an article. This is
    deliberate: a test that passes only because the bar is low establishes
    nothing about whether the bar works.
    """
    para = (
        "Refrigeration investment is finally following the produce rather "
        "than the retail. Post-harvest losses remain among the highest in the "
        "region, and most of them occur within a day of picking. Cold chain "
        "capital has historically favoured urban retail environments over the "
        "point of harvest, which is the imbalance now correcting."
    )
    return "".join(f"<p>{para}</p>" for _ in range(paragraphs))


def draft_payload(title, category="Tech", **extra):
    return {
        "title": title,
        "excerpt": "A logistics problem is quietly reshaping the sector.",
        "body": draft_copy(),
        "category": category,
        **extra,
    }



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
            draft_payload("AI in Everyday Workspaces", "Business"),
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
            draft_payload("Sustainable Tech in 2026"),
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
            draft_payload("Not Ready Yet"),
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
            **draft_payload("Gate Test")})
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

    def _upload(self, client, issue, version="v1.0", cover=True):
        """A first layout must carry a cover image — it is what readers see in
        the archive. Later versions inherit it."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("layout.pdf", b"%PDF-1.4 fake",
                               content_type="application/pdf")
        payload = {"issue": issue.id, "version": version, "file": f,
                   "notes_to_editor": "First pass."}
        if cover:
            payload["cover_image"] = _tiny_png()
        return client.post("/api/design/designs/", payload, format="multipart")

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

        f = SimpleUploadedFile("layout.indd", b"nope",
                               content_type="application/octet-stream")
        r = auth_client(designer).post("/api/design/designs/",
            {"issue": issue.id, "version": "v1.0", "file": f}, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDesignerArticleAccess:
    """Designers lay out issues, not loose articles.

    Approval is an editorial milestone; the handover to production is
    assignment to an issue, because that is when the article has a page to sit
    on. A designer shown approved-but-unassigned copy would be looking at work
    they cannot act on.
    """

    def _designer(self, make_user, email):
        from apps.accounts.models import User
        return make_user(email, User.Role.GRAPHIC_DESIGNER)

    def _issue(self, publisher, number=70):
        from apps.issues.models import Issue
        return Issue.objects.create(number=number, title="Layout Issue",
                                    created_by=publisher)

    def test_designer_sees_approved_copy_that_is_in_an_issue(
        self, auth_client, make_user, writer, publisher
    ):
        designer = self._designer(make_user, "designer4@boss.ph")
        issue = self._issue(publisher, 71)

        in_issue = Article.objects.create(
            writer=writer, title="Ready for layout", body="<p>Final copy.</p>",
            category="Tech", status=Article.Status.APPROVED, issue=issue)

        r = auth_client(designer).get("/api/editorial/articles/")
        ids = [a["id"] for a in r.data["results"]]
        assert in_issue.id in ids

    def test_approved_copy_without_an_issue_is_not_theirs_yet(
        self, auth_client, make_user, writer
    ):
        designer = self._designer(make_user, "designer4b@boss.ph")

        unassigned = Article.objects.create(
            writer=writer, title="Approved, unscheduled", body="<p>Copy.</p>",
            category="Tech", status=Article.Status.APPROVED)

        r = auth_client(designer).get("/api/editorial/articles/")
        ids = [a["id"] for a in r.data["results"]]
        assert unassigned.id not in ids, (
            "Approved copy with no issue is still an editorial decision, "
            "not production work"
        )

    def test_drafts_are_never_visible_to_a_designer(
        self, auth_client, make_user, writer, publisher
    ):
        designer = self._designer(make_user, "designer4c@boss.ph")
        issue = self._issue(publisher, 72)

        draft = Article.objects.create(
            writer=writer, title="Not ready", body="<p>Notes.</p>",
            category="Tech", status=Article.Status.DRAFTING, issue=issue)

        r = auth_client(designer).get("/api/editorial/articles/")
        ids = [a["id"] for a in r.data["results"]]
        assert draft.id not in ids

    def test_designer_can_read_the_body_of_copy_in_their_issue(
        self, auth_client, make_user, writer, publisher
    ):
        designer = self._designer(make_user, "designer5@boss.ph")
        issue = self._issue(publisher, 73)

        a = Article.objects.create(
            writer=writer, title="Layout me", body="<p>Body for layout.</p>",
            category="Life", status=Article.Status.APPROVED, issue=issue)

        r = auth_client(designer).get(f"/api/editorial/articles/{a.id}/")
        assert r.status_code == status.HTTP_200_OK
        assert "Body for layout" in r.data["body"]


@pytest.mark.django_db
class TestPullBack:
    """Approval is reversible until publication, but ownership moves to the
    publisher once an article is assigned to an issue."""

    def _approved(self, writer, issue=None):
        return Article.objects.create(
            writer=writer, title="Approved piece", body="<p>Copy.</p>",
            category="Tech", status=Article.Status.APPROVED, issue=issue)

    def test_editor_can_pull_back_an_unassigned_article(
        self, auth_client, writer, editor
    ):
        a = self._approved(writer)
        r = auth_client(editor).post(
            f"/api/editorial/articles/{a.id}/pull-back/", {"reason": "Sources unverified."})
        assert r.status_code == status.HTTP_200_OK
        a.refresh_from_db()
        assert a.status == Article.Status.UNDER_REVIEW

    def test_editor_cannot_pull_back_once_it_is_in_an_issue(
        self, auth_client, writer, editor, publisher
    ):
        from apps.issues.models import Issue
        issue = Issue.objects.create(number=40, title="Test", created_by=publisher)
        a = self._approved(writer, issue)

        r = auth_client(editor).post(
            f"/api/editorial/articles/{a.id}/pull-back/", {"reason": "Changed my mind."})
        assert r.status_code == status.HTTP_403_FORBIDDEN
        a.refresh_from_db()
        assert a.status == Article.Status.APPROVED

    def test_publisher_pull_back_removes_it_from_the_issue(
        self, auth_client, writer, publisher
    ):
        from apps.issues.models import Issue
        issue = Issue.objects.create(number=41, title="Test", created_by=publisher)
        a = self._approved(writer, issue)

        r = auth_client(publisher).post(
            f"/api/editorial/articles/{a.id}/pull-back/", {"reason": "Holding for next month."})
        assert r.status_code == status.HTTP_200_OK

        a.refresh_from_db()
        assert a.status == Article.Status.UNDER_REVIEW
        # The issue must not be left permanently unpublishable.
        assert a.issue_id is None
        assert issue.articles.count() == 0

    def test_a_reason_is_required(self, auth_client, writer, editor):
        a = self._approved(writer)
        r = auth_client(editor).post(
            f"/api/editorial/articles/{a.id}/pull-back/", {"reason": "no"})
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLayoutRequirements:
    """The layout is the edition subscribers read, so it must be a PDF, and
    the first one must bring the cover the archive displays."""

    def _issue(self, publisher, number=60):
        from apps.issues.models import Issue
        return Issue.objects.create(number=number, title="Test Issue",
                                    created_by=publisher)

    def _designer(self, make_user, email):
        from apps.accounts.models import User
        return make_user(email, User.Role.GRAPHIC_DESIGNER)

    def test_first_layout_requires_a_cover(self, auth_client, make_user, publisher):
        from django.core.files.uploadedfile import SimpleUploadedFile
        d = self._designer(make_user, "cover1@boss.ph")
        issue = self._issue(publisher, 61)

        r = auth_client(d).post("/api/design/designs/", {
            "issue": issue.id, "version": "v1.0",
            "file": SimpleUploadedFile("l.pdf", b"%PDF-1.4", content_type="application/pdf"),
        }, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "cover_image" in r.data

    def test_a_working_file_is_rejected(self, auth_client, make_user, publisher):
        from django.core.files.uploadedfile import SimpleUploadedFile
        d = self._designer(make_user, "cover2@boss.ph")
        issue = self._issue(publisher, 62)

        r = auth_client(d).post("/api/design/designs/", {
            "issue": issue.id, "version": "v1.0",
            "file": SimpleUploadedFile("l.indd", b"x", content_type="application/octet-stream"),
            "cover_image": _tiny_png(),
        }, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_an_issue_below_its_minimum_is_not_ready(self, writer, publisher):
        from apps.editorial.models import Article
        from apps.issues.models import Issue
        issue = Issue.objects.create(number=63, title="Big Issue",
                                     minimum_articles=3, created_by=publisher)
        Article.objects.create(writer=writer, title="Only one",
                               body="<p>x</p>", category="Tech",
                               status=Article.Status.APPROVED, issue=issue)

        assert issue.is_ready is False
        assert any("2 more" in r for r in issue.blocking_reasons())


@pytest.mark.django_db
class TestIssueClosingAndPublishing:
    """UC-2.2 Compile Issue and UC-2.5 Execute Live Publishing.

    An issue goes to press closed: the table of contents is fixed so the art
    department can lay out pages knowing they will not be redone. These tests
    cover the lock, the reopening that keeps it workable, and the atomic
    publication itself.
    """

    def _issue(self, publisher, number=80, minimum=1):
        from apps.issues.models import Issue
        return Issue.objects.create(number=number, title="Test Issue",
                                    minimum_articles=minimum,
                                    created_by=publisher)

    def _approved(self, writer, issue):
        return Article.objects.create(
            writer=writer, title="Ready copy", body="<p>Final.</p>",
            category="Tech", status=Article.Status.APPROVED, issue=issue)

    def _layout(self, issue, designer):
        from django.core.files.base import ContentFile
        from apps.design.models import MagazineDesign
        d = MagazineDesign.objects.create(
            issue=issue, version="v1.0", designer=designer,
            status=MagazineDesign.Status.APPROVED)
        d.file.save("layout.pdf", ContentFile(b"%PDF-1.4"), save=True)
        return d

    def _designer(self, make_user, email):
        from apps.accounts.models import User
        return make_user(email, User.Role.GRAPHIC_DESIGNER)

    # ---- closing ----------------------------------------------------------

    def test_closing_fixes_the_contents(self, auth_client, writer, publisher):
        from apps.issues.models import Issue
        issue = self._issue(publisher, 81)
        self._approved(writer, issue)

        r = auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")
        assert r.status_code == status.HTTP_200_OK

        issue.refresh_from_db()
        assert issue.status == Issue.Status.COMPILED
        assert issue.closed_at is not None
        assert issue.is_closed

    def test_an_empty_issue_cannot_be_closed(self, auth_client, publisher):
        issue = self._issue(publisher, 82)
        r = auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_a_closed_issue_refuses_new_articles(
        self, auth_client, writer, editor, publisher
    ):
        issue = self._issue(publisher, 83)
        self._approved(writer, issue)
        auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")

        loose = Article.objects.create(
            writer=writer, title="Late piece", body="<p>x</p>",
            category="Life", status=Article.Status.APPROVED)

        r = auth_client(editor).post(
            f"/api/editorial/articles/{loose.id}/assign-issue/", {"issue": issue.id})
        assert r.status_code == status.HTTP_409_CONFLICT
        assert "closed" in r.data["detail"].lower()

    def test_reopening_requires_a_reason_and_restores_assignment(
        self, auth_client, writer, editor, publisher
    ):
        from apps.issues.models import Issue
        issue = self._issue(publisher, 84)
        self._approved(writer, issue)
        auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")

        bare = auth_client(publisher).post(
            f"/api/publication/issues/{issue.id}/reopen/", {"reason": "no"})
        assert bare.status_code == status.HTTP_400_BAD_REQUEST

        ok = auth_client(publisher).post(
            f"/api/publication/issues/{issue.id}/reopen/",
            {"reason": "Late feature confirmed for this issue."})
        assert ok.status_code == status.HTTP_200_OK

        issue.refresh_from_db()
        assert issue.status == Issue.Status.PLANNING
        assert not issue.is_closed
        assert "Late feature" in issue.reopen_reason

    # ---- publishing -------------------------------------------------------

    def test_an_open_issue_cannot_be_published(
        self, auth_client, writer, publisher, make_user
    ):
        issue = self._issue(publisher, 85)
        self._approved(writer, issue)
        self._layout(issue, self._designer(make_user, "d85@boss.ph"))

        r = auth_client(publisher).post(f"/api/publication/issues/{issue.id}/publish/")
        assert r.status_code == status.HTTP_409_CONFLICT
        assert any("not been closed" in x for x in r.data["reasons"])

    def test_publishing_releases_every_article_together(
        self, auth_client, writer, publisher, make_user
    ):
        from apps.issues.models import Issue
        issue = self._issue(publisher, 86, minimum=2)
        a1 = self._approved(writer, issue)
        a2 = self._approved(writer, issue)
        self._layout(issue, self._designer(make_user, "d86@boss.ph"))

        auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")
        r = auth_client(publisher).post(f"/api/publication/issues/{issue.id}/publish/")
        assert r.status_code == status.HTTP_200_OK

        issue.refresh_from_db(); a1.refresh_from_db(); a2.refresh_from_db()
        assert issue.status == Issue.Status.PUBLISHED
        assert a1.status == Article.Status.PUBLISHED
        assert a2.status == Article.Status.PUBLISHED
        assert a1.published_at is not None

    def test_an_unapproved_article_blocks_publication(
        self, auth_client, writer, publisher, make_user
    ):
        issue = self._issue(publisher, 87)
        self._approved(writer, issue)
        Article.objects.create(writer=writer, title="Still in review",
                               body="<p>x</p>", category="Tech",
                               status=Article.Status.UNDER_REVIEW, issue=issue)
        self._layout(issue, self._designer(make_user, "d87@boss.ph"))
        auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")

        r = auth_client(publisher).post(f"/api/publication/issues/{issue.id}/publish/")
        assert r.status_code == status.HTTP_409_CONFLICT
        assert any("not yet approved" in x for x in r.data["reasons"])

    def test_publishing_without_a_layout_is_refused(
        self, auth_client, writer, publisher
    ):
        """The layout is the edition. An issue without one has nothing to
        publish."""
        from apps.issues.models import Issue
        issue = self._issue(publisher, 88)
        self._approved(writer, issue)
        auth_client(publisher).post(f"/api/publication/issues/{issue.id}/close/")

        r = auth_client(publisher).post(f"/api/publication/issues/{issue.id}/publish/")
        assert r.status_code == status.HTTP_409_CONFLICT
        assert any("no approved layout" in x.lower() for x in r.data["reasons"])

        issue.refresh_from_db()
        assert issue.status != Issue.Status.PUBLISHED


@pytest.mark.django_db
class TestEntitlement:
    """Who may read paid content.

    The check governs the paywall in three places, so it is asserted here
    rather than left to whichever endpoint happens to be exercised.
    """

    def _premium(self, writer, issue=None):
        return Article.objects.create(
            writer=writer, title="Behind the cold chain",
            body="<p>" + ("Reporting. " * 80) + "</p>",
            excerpt="A logistics problem reshaping the sector.",
            category="Business", status=Article.Status.PUBLISHED,
            is_premium=True, issue=issue, published_at=timezone.now())

    def test_free_reader_gets_the_extract(self, api_client, writer, make_user):
        from apps.accounts.models import User
        article = self._premium(writer)
        reader = make_user("free@boss.ph", User.Role.READER)

        api_client.force_authenticate(reader)
        r = api_client.get(f"/api/content/articles/{article.id}/")
        assert r.status_code == status.HTTP_200_OK
        assert r.data["is_locked"] is True

    def test_subscriber_gets_the_full_article(self, api_client, writer, make_user):
        from apps.accounts.models import ReaderProfile, User
        article = self._premium(writer)
        reader = make_user("sub@boss.ph", User.Role.READER)
        ReaderProfile.objects.update_or_create(
            user=reader, defaults={"tier": ReaderProfile.Tier.SUBSCRIBER})
        # The fixture already created a FREE profile, and the user object
        # still holds it cached; without this the request is authenticated
        # as the tier that was replaced.
        reader.refresh_from_db()

        api_client.force_authenticate(reader)
        r = api_client.get(f"/api/content/articles/{article.id}/")
        assert r.data["is_locked"] is False

    def test_staff_read_the_magazine_they_produce(
        self, api_client, writer, editor, publisher, make_user
    ):
        """The paywall monetises readers; it does not obstruct the people
        making the magazine. An editor following the public-site link should
        see the article, not a subscription notice."""
        from apps.accounts.models import User
        article = self._premium(writer)

        designer = make_user("d-ent@boss.ph", User.Role.GRAPHIC_DESIGNER)
        for staff in (editor, publisher, designer, writer):
            api_client.force_authenticate(staff)
            r = api_client.get(f"/api/content/articles/{article.id}/")
            assert r.data["is_locked"] is False, f"{staff.role} was paywalled"

    def test_a_suspended_account_is_refused(self, api_client, writer, editor):
        """Suspension precedes every role, so it precedes this too."""
        article = self._premium(writer)
        editor.is_suspended = True
        editor.save(update_fields=["is_suspended"])

        api_client.force_authenticate(editor)
        r = api_client.get(f"/api/content/articles/{article.id}/")
        assert r.data["is_locked"] is True

    def test_anonymous_is_refused(self, api_client, writer):
        article = self._premium(writer)
        r = api_client.get(f"/api/content/articles/{article.id}/")
        assert r.data["is_locked"] is True


@pytest.mark.django_db
def test_an_issue_article_cannot_be_published_on_its_own(auth_client, writer, publisher):
    """Publishing issue articles one at a time would put the issue live
    without its approved layout. They are released with the issue only."""
    from apps.issues.models import Issue
    issue = Issue.objects.create(number=95, title="Held", created_by=publisher)
    article = Article.objects.create(
        writer=writer, title="In an issue", body="<p>Final.</p>",
        category="Tech", status=Article.Status.APPROVED, issue=issue)

    r = auth_client(publisher).post(f"/api/editorial/articles/{article.id}/publish/")
    assert r.status_code == status.HTTP_409_CONFLICT
    article.refresh_from_db()
    assert article.status == Article.Status.APPROVED


@pytest.mark.django_db
def test_an_issue_without_a_layout_is_not_ready(writer, publisher):
    """Readiness and publication must agree. An issue whose copy is complete
    but which has no approved layout is not ready, and says why."""
    from apps.issues.models import Issue
    issue = Issue.objects.create(number=96, title="No layout", minimum_articles=1,
                                 created_by=publisher)
    Article.objects.create(writer=writer, title="Done", body="<p>Final.</p>",
                           category="Tech", status=Article.Status.APPROVED, issue=issue)
    assert issue.is_ready is False
    assert any("No approved layout" in r for r in issue.blocking_reasons())


FLAWED = "The findings suggests the market are changing."
FIXES = [
    {"id": "f1", "original": "The findings suggests", "replacement": "The findings suggest",
     "reason": "Plural subject.", "note_type": "GRAMMAR"},
    {"id": "f2", "original": "market are changing", "replacement": "market is changing",
     "reason": "Singular subject.", "note_type": "GRAMMAR"},
]


@pytest.mark.django_db
class TestQuickFixes:
    """Three verdicts, and quick fixes for the middle one.

    The score never moves because a fix was accepted; it is re-measured on
    resubmission. What these tests guard is that fixes change exactly the
    words they claim to, once, and only while the article is with its writer.
    """

    def _submit(self, client, monkeypatch, score, fixes=FIXES, body=None):
        monkeypatch.setattr("apps.editorial.views.evaluate_article", lambda a: {
            "grammar_score": score, "readability_score": score, "overall_score": score,
            "recommendation": "APPROVE" if score >= 70 else "REJECT",
            "summary": "Assessment.", "suggestions": [], "fixes": [dict(f) for f in fixes],
            "raw_response": {}, "ai_model": "test"})
        r = client.post("/api/editorial/articles/",
                        draft_payload("Quick fixes", body=body or draft_copy() + f"<p>{FLAWED}</p>"),
                        format="json")
        assert r.status_code == 201, r.data
        aid = r.data["id"]
        sub = client.post(f"/api/editorial/articles/{aid}/submit/")
        return aid, sub

    def test_the_middle_band_returns_with_fixes(self, auth_client, writer, monkeypatch):
        from apps.ai_eval.models import ArticleEvaluation
        aid, sub = self._submit(auth_client(writer), monkeypatch, 55)
        assert sub.data["verdict"] == "REVISE"
        a = Article.objects.get(pk=aid)
        assert a.status == Article.Status.REVISION_REQUESTED
        assert len(a.evaluations.first().fixes) == 2

    def test_a_rewrite_gets_no_fixes(self, auth_client, writer, monkeypatch):
        aid, sub = self._submit(auth_client(writer), monkeypatch, 30)
        assert sub.data["verdict"] == "REWRITE"
        a = Article.objects.get(pk=aid)
        assert a.status == Article.Status.REVISION_REQUESTED
        assert a.evaluations.first().fixes == []

    def test_a_pass_gets_no_fixes(self, auth_client, writer, monkeypatch):
        aid, sub = self._submit(auth_client(writer), monkeypatch, 85)
        assert sub.data["verdict"] == "PASS"
        a = Article.objects.get(pk=aid)
        assert a.status == Article.Status.UNDER_REVIEW
        assert a.evaluations.first().fixes == []

    def test_applying_a_fix_changes_exactly_that_passage(self, auth_client, writer, monkeypatch):
        from apps.ai_eval.models import FixDecision
        c = auth_client(writer)
        aid, _ = self._submit(c, monkeypatch, 55)
        r = c.post(f"/api/editorial/articles/{aid}/fixes/f1/apply/")
        assert r.status_code == 200, r.data
        assert "The findings suggest the market are changing." in r.data["body"]
        assert FixDecision.objects.filter(fix_id="f1", action="ACCEPTED").count() == 1
        states = {f["id"]: f["state"] for f in r.data["evaluation"]["fixes"]}
        assert states == {"f1": "accepted", "f2": "pending"}
        assert r.data["evaluation"]["overall_score"] == 55

    def test_an_edited_passage_makes_its_fix_stale(self, auth_client, writer, monkeypatch):
        from apps.ai_eval.models import FixDecision
        c = auth_client(writer)
        aid, _ = self._submit(c, monkeypatch, 55)
        c.patch(f"/api/editorial/articles/{aid}/", {"body": draft_copy()}, format="json")
        r = c.post(f"/api/editorial/articles/{aid}/fixes/f2/apply/")
        assert r.status_code == 409 and r.data["state"] == "stale"
        assert not FixDecision.objects.filter(fix_id="f2").exists()

    def test_a_fix_is_decided_once(self, auth_client, writer, monkeypatch):
        c = auth_client(writer)
        aid, _ = self._submit(c, monkeypatch, 55)
        assert c.post(f"/api/editorial/articles/{aid}/fixes/f1/dismiss/").status_code == 200
        assert c.post(f"/api/editorial/articles/{aid}/fixes/f1/apply/").status_code == 409
        assert FLAWED in Article.objects.get(pk=aid).body

    def test_only_the_writer_acts_on_fixes(self, auth_client, writer, make_user, monkeypatch):
        from apps.accounts.models import User
        aid, _ = self._submit(auth_client(writer), monkeypatch, 55)
        other = make_user("other-writer@boss.ph", User.Role.WRITER)
        r = auth_client(other).post(f"/api/editorial/articles/{aid}/fixes/f1/apply/")
        assert r.status_code in (403, 404)

    def test_fixes_close_once_the_article_leaves_the_writer(self, auth_client, writer, monkeypatch):
        c = auth_client(writer)
        aid, _ = self._submit(c, monkeypatch, 55)
        Article.objects.filter(pk=aid).update(status=Article.Status.UNDER_REVIEW)
        assert c.post(f"/api/editorial/articles/{aid}/fixes/f1/apply/").status_code == 409

    def test_resolving_every_fix_lifts_the_cooldown(self, auth_client, writer, monkeypatch):
        c = auth_client(writer)
        aid, _ = self._submit(c, monkeypatch, 55)
        c.post(f"/api/editorial/articles/{aid}/fixes/f1/apply/")
        c.post(f"/api/editorial/articles/{aid}/fixes/f2/apply/")
        r = c.post(f"/api/editorial/articles/{aid}/submit/")
        assert r.status_code == 201, r.data

    def test_the_cooldown_holds_while_fixes_are_pending(self, auth_client, writer, monkeypatch):
        c = auth_client(writer)
        aid, _ = self._submit(c, monkeypatch, 55)
        c.patch(f"/api/editorial/articles/{aid}/",
                {"body": draft_copy() + f"<p>{FLAWED} Extra.</p>"}, format="json")
        r = c.post(f"/api/editorial/articles/{aid}/submit/")
        assert r.status_code == 400
        assert any("rate-limited" in x for x in r.data["reasons"])

    def test_no_credential_means_review_without_assessment(self, auth_client, writer, monkeypatch):
        from apps.ai_eval.services import EvaluationUnavailable
        def unavailable(a): raise EvaluationUnavailable("none")
        monkeypatch.setattr("apps.editorial.views.evaluate_article", unavailable)
        c = auth_client(writer)
        r = c.post("/api/editorial/articles/", draft_payload("No key"), format="json")
        sub = c.post(f"/api/editorial/articles/{r.data['id']}/submit/")
        assert sub.data["gate"] == "BYPASSED"
        a = Article.objects.get(pk=r.data["id"])
        assert a.status == Article.Status.UNDER_REVIEW and a.returned_by_ai is False


def test_the_real_service_raises_without_a_credential(settings):
    from apps.ai_eval.services import EvaluationUnavailable, evaluate_article
    settings.ANTHROPIC_API_KEY = ""
    with pytest.raises(EvaluationUnavailable):
        evaluate_article(None)


def test_fixes_that_cannot_be_located_are_dropped(settings):
    from apps.ai_eval.fixes import apply_fix, clean_fixes
    settings.AI_MAX_FIXES = 8
    body = "<p>One two. One two.</p><p>Salt &amp; pepper, <b>bold</b> text.</p>"
    kept = clean_fixes([
        {"original": "One two", "replacement": "Three"},        # appears twice
        {"original": "missing", "replacement": "x"},            # not there
        {"original": "same", "replacement": "same"},            # no change
        {"original": "pepper, bold", "replacement": "x"},       # spans a tag
        {"original": "Salt & pepper", "replacement": "Salt & ground pepper"},
    ], body)
    assert [f["original"] for f in kept] == ["Salt & pepper"]
    assert kept[0]["id"] == "f1"
    out = apply_fix(body, kept[0])
    assert "Salt &amp; ground pepper" in out and "<b>bold</b>" in out
