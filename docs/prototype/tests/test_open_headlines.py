"""Open headlines: an editor plans a headline with no writer, then gives
it to a writer later (adviser meeting, Nov 24)."""
import pytest
from django.db import IntegrityError

from apps.accounts.models import User
from apps.editorial.models import Article
from apps.notifications.models import Notification

ASSIGN = "/api/editorial/articles/assign/"


def headline(client, **extra):
    return client.post(ASSIGN, {"title": "Coffee chains in Cebu", **extra}, format="json")


@pytest.mark.django_db
class TestOpenHeadline:
    def test_no_writer_puts_it_in_the_backlog(self, auth_client, editor):
        r = headline(auth_client(editor), brief="Who is opening where", category="Business")
        assert r.status_code == 201
        a = Article.objects.get()
        assert a.status == Article.Status.OPEN and a.writer is None
        assert a.assigned_by == editor
        assert r.json()["writer_name"] is None

    def test_with_a_writer_it_is_assigned_as_before(self, auth_client, editor, writer):
        r = headline(auth_client(editor), writer=writer.pk)
        assert r.status_code == 201
        assert Article.objects.get().status == Article.Status.ASSIGNED
        assert Notification.objects.filter(recipient=writer).exists()

    def test_editors_see_it_writers_do_not(self, auth_client, editor, writer):
        headline(auth_client(editor))
        rows = auth_client(editor).get("/api/editorial/articles/").json()
        rows = rows.get("results", rows)
        assert [r["status"] for r in rows] == ["OPEN"] and rows[0]["writer_name"] is None
        mine = auth_client(writer).get("/api/editorial/articles/").json()
        assert not mine.get("results", mine)

    def test_only_an_open_headline_may_lack_a_writer(self, editor):
        with pytest.raises(IntegrityError):
            Article.objects.create(title="T", body="", status=Article.Status.ASSIGNED,
                                   assigned_by=editor)

    def test_the_calendar_and_timeline_cope_without_a_writer(self, auth_client, editor):
        c = auth_client(editor)
        headline(c, deadline="2026-12-10")
        a = Article.objects.get()
        cal = c.get("/api/editorial/articles/calendar/?year=2026&month=12")
        assert cal.status_code == 200
        assert cal.json()["events"][0]["writer"] == "Unassigned"
        assert c.get(f"/api/editorial/articles/{a.pk}/timeline/").status_code == 200

    def test_pipeline_counts_it(self, auth_client, editor):
        c = auth_client(editor)
        headline(c)
        assert c.get("/api/editorial/articles/pipeline/").json()["by_status"]["OPEN"] == 1


@pytest.mark.django_db
class TestGiveToWriter:
    def url(self, a):
        return f"/api/editorial/articles/{a.pk}/assign-writer/"

    def test_the_writer_gets_it_and_is_told(self, auth_client, editor, writer):
        c = auth_client(editor)
        headline(c)
        a = Article.objects.get()
        r = c.post(self.url(a), {"writer": writer.pk, "deadline": "2026-12-15"}, format="json")
        assert r.status_code == 200
        a.refresh_from_db()
        assert a.writer == writer and a.status == Article.Status.ASSIGNED
        assert str(a.deadline) == "2026-12-15"
        assert Notification.objects.filter(recipient=writer,
                                           message__contains="assigned").exists()

    def test_only_an_active_writer(self, auth_client, editor, writer):
        c = auth_client(editor)
        headline(c)
        a = Article.objects.get()
        User.objects.filter(pk=writer.pk).update(is_suspended=True)
        assert c.post(self.url(a), {"writer": writer.pk}, format="json").status_code == 400
        assert c.post(self.url(a), {"writer": editor.pk}, format="json").status_code == 400

    def test_not_for_an_article_already_assigned(self, auth_client, editor, writer):
        c = auth_client(editor)
        headline(c, writer=writer.pk)
        a = Article.objects.get()
        assert c.post(self.url(a), {"writer": writer.pk}, format="json").status_code == 409

    def test_a_writer_cannot_take_one(self, auth_client, editor, writer):
        headline(auth_client(editor))
        a = Article.objects.get()
        r = auth_client(writer).post(self.url(a), {"writer": writer.pk}, format="json")
        assert r.status_code in (403, 404)

    def test_a_headline_can_be_dropped(self, auth_client, editor):
        c = auth_client(editor)
        headline(c)
        a = Article.objects.get()
        r = c.post(f"/api/editorial/articles/{a.pk}/withdraw/",
                   {"reason": "Story went stale"}, format="json")
        assert r.status_code == 200
        a.refresh_from_db()
        assert a.status == Article.Status.WITHDRAWN
