"""Who may read what (adviser meeting, Nov 24: "getters expose all user and
system information"). Each staff endpoint refuses readers, and the narrower
ones refuse staff who have no use for them. A field or endpoint that leaks
again fails here."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.editorial.models import Article, ArticleImage

STAFF_ONLY = [
    "/api/editorial/articles/", "/api/editorial/articles/archive-facets/",
    "/api/editorial/images/", "/api/editorial/categories/",
    "/api/ai-eval/evaluations/", "/api/design/designs/",
    "/api/publication/issues/", "/api/messages/",
    "/api/reports/pipeline/", "/api/reports/evaluation/", "/api/reports/production/",
    "/api/editorial/articles/pipeline/", "/api/editorial/articles/facets/",
    "/api/editorial/articles/calendar/",
]
# Endpoints a writer has no use for.
NOT_FOR_WRITERS = [
    "/api/design/designs/", "/api/reports/pipeline/", "/api/reports/evaluation/",
    "/api/reports/production/", "/api/editorial/articles/pipeline/",
    "/api/editorial/articles/facets/",
]


def client_for(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user)
    return c


@pytest.fixture
def reader(make_user):
    return make_user("reader@boss.ph", User.Role.READER)


@pytest.mark.django_db
class TestReadersAreNotStaff:
    @pytest.mark.parametrize("url", STAFF_ONLY)
    def test_a_reader_is_refused(self, reader, url):
        assert client_for(reader).get(url).status_code == 403

    @pytest.mark.parametrize("url", STAFF_ONLY)
    def test_nobody_signed_out_gets_in(self, url):
        assert client_for().get(url).status_code == 401

    def test_a_reader_cannot_open_a_draft(self, reader, writer):
        a = Article.objects.create(title="Draft", body="<p>secret</p>", writer=writer,
                                   status=Article.Status.DRAFTING)
        assert client_for(reader).get(f"/api/editorial/articles/{a.pk}/").status_code == 403

    def test_a_reader_cannot_create_an_article(self, reader):
        r = client_for(reader).post("/api/editorial/articles/", {"title": "Mine"}, format="json")
        assert r.status_code == 403 and not Article.objects.exists()


@pytest.mark.django_db
class TestStaffSeeOnlyWhatTheyUse:
    @pytest.mark.parametrize("url", NOT_FOR_WRITERS)
    def test_a_writer_is_refused(self, writer, url):
        assert client_for(writer).get(url).status_code == 403

    def test_editors_and_publishers_keep_their_reports(self, editor, publisher):
        for u in (editor, publisher):
            for url in ("/api/reports/pipeline/", "/api/reports/production/"):
                assert client_for(u).get(url).status_code == 200, (u.role, url)

    def test_a_writer_sees_only_photographs_on_their_own_articles(self, writer, make_user):
        other = make_user("teo@boss.ph", User.Role.WRITER)
        theirs = Article.objects.create(title="T", body="", writer=other)
        ArticleImage.objects.create(article=theirs, image="articles/x.jpg")
        rows = client_for(writer).get("/api/editorial/images/").json()
        assert (rows.get("results", rows) if isinstance(rows, dict) else rows) == []


@pytest.mark.django_db
class TestPlatformSettings:
    def test_the_public_sees_the_site_not_the_services(self):
        data = client_for().get("/api/platform/settings/").json()
        assert "site_name" in data and "maintenance_mode" in data
        assert "integrations" not in data and "updated_at" not in data

    def test_the_administrator_sees_the_services(self, make_user):
        admin = make_user("admin@boss.ph", User.Role.ADMIN)
        assert "integrations" in client_for(admin).get("/api/platform/settings/").json()
