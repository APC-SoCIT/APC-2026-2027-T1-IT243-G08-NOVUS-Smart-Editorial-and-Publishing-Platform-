"""All articles: one list of every article with search, filters and sort
(adviser meeting, Nov 24)."""
import pytest

from apps.accounts.models import User
from apps.editorial.models import Article

LIST = "/api/editorial/articles/"


@pytest.fixture
def pipeline(editor, writer, make_user):
    teo = make_user("teo@boss.ph", User.Role.WRITER)
    S = Article.Status
    make = lambda **kw: Article.objects.create(body="", assigned_by=editor, **kw)
    return {
        "open": make(title="Coffee in Cebu", status=S.OPEN, category="Business",
                     deadline="2020-01-01"),
        "draft": make(title="Night markets", status=S.DRAFTING, writer=writer, category="Life"),
        "review": make(title="Solar rooftops", status=S.UNDER_REVIEW, writer=teo, category=""),
        "pub": make(title="Design studios", status=S.PUBLISHED, writer=teo, category="Business"),
    }


def titles(r):
    data = r.json()
    return [a["title"] for a in data.get("results", data)]


@pytest.mark.django_db
class TestAllArticles:
    def test_every_article_with_labels(self, auth_client, editor, pipeline):
        r = auth_client(editor).get(LIST)
        assert r.status_code == 200 and r.json()["count"] == 4
        row = next(a for a in r.json()["results"] if a["title"] == "Coffee in Cebu")
        assert row["writer_name"] is None and row["status_label"] == "Open"

    def test_unassigned_and_uncategorised_filters(self, auth_client, editor, pipeline):
        c = auth_client(editor)
        assert titles(c.get(LIST, {"writer": "none"})) == ["Coffee in Cebu"]
        assert titles(c.get(LIST, {"category": "none"})) == ["Solar rooftops"]
        assert titles(c.get(LIST, {"writer": "abc"})) == []

    def test_search_covers_category_and_writer(self, auth_client, editor, pipeline):
        c = auth_client(editor)
        assert set(titles(c.get(LIST, {"q": "business"}))) == {"Coffee in Cebu", "Design studios"}
        assert set(titles(c.get(LIST, {"q": "Test"}))) == {"Night markets", "Solar rooftops", "Design studios"}

    def test_overdue_includes_an_open_headline(self, auth_client, editor, pipeline):
        assert titles(auth_client(editor).get(LIST, {"overdue": "true"})) == ["Coffee in Cebu"]

    def test_sort_by_title_and_status(self, auth_client, editor, pipeline):
        c = auth_client(editor)
        assert titles(c.get(LIST, {"sort": "title"}))[0] == "Coffee in Cebu"
        assert titles(c.get(LIST, {"sort": "-title"}))[0] == "Solar rooftops"

    def test_page_size(self, auth_client, editor, pipeline):
        r = auth_client(editor).get(LIST, {"page_size": 2})
        assert len(r.json()["results"]) == 2 and r.json()["next"]

    def test_facets_for_a_publisher(self, auth_client, publisher, pipeline):
        f = auth_client(publisher).get(LIST + "facets/").json()
        assert f["categories"] == ["Business", "Life"]
        assert len(f["writers"]) == 2 and f["has_unassigned"] is True
        assert {"value": "OPEN", "label": "Open"} in f["statuses"]

    def test_a_writer_still_sees_only_their_own(self, auth_client, writer, pipeline):
        assert titles(auth_client(writer).get(LIST)) == ["Night markets"]
