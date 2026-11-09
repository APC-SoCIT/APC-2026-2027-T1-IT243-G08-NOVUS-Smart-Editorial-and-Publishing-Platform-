"""UC-1.1 A3: an Editor moves an assignment to another Writer."""
import pytest

from apps.accounts.models import User
from apps.editorial.models import Article
from apps.notifications.models import Notification


@pytest.fixture
def second_writer(make_user):
    return make_user("teo@boss.ph", User.Role.WRITER)


def assigned(editor, writer, status=Article.Status.ASSIGNED, body=""):
    return Article.objects.create(writer=writer, assigned_by=editor, editor=editor,
                                  title="Port congestion", body=body, category="Business",
                                  status=status)


def reassign(client, article, writer_id, **extra):
    return client.post(f"/api/editorial/articles/{article.pk}/reassign/",
                       {"writer": writer_id, **extra}, format="json")


@pytest.mark.django_db
class TestReassign:
    def test_the_draft_moves_and_both_writers_are_told(
        self, auth_client, editor, writer, second_writer
    ):
        a = assigned(editor, writer, Article.Status.DRAFTING, body="<p>First half.</p>")
        r = reassign(auth_client(editor), a, second_writer.pk, deadline="2026-12-01")
        assert r.status_code == 200
        a.refresh_from_db()
        assert a.writer == second_writer and a.body == "<p>First half.</p>"
        assert str(a.deadline) == "2026-12-01"
        assert Notification.objects.filter(recipient=second_writer, message__contains="reassigned to you").exists()
        assert Notification.objects.filter(recipient=writer, message__contains="moved to another writer").exists()

    def test_a_submitted_article_cannot_be_reassigned(
        self, auth_client, editor, writer, second_writer
    ):
        a = assigned(editor, writer, Article.Status.UNDER_REVIEW)
        assert reassign(auth_client(editor), a, second_writer.pk).status_code == 409

    def test_only_an_active_writer_can_take_it(self, auth_client, editor, writer, second_writer):
        a = assigned(editor, writer)
        c = auth_client(editor)
        User.objects.filter(pk=second_writer.pk).update(is_suspended=True)
        assert reassign(c, a, second_writer.pk).status_code == 400
        assert reassign(c, a, editor.pk).status_code == 400
        assert reassign(c, a, writer.pk).status_code == 400      # already theirs

    def test_a_bad_deadline_is_refused(self, auth_client, editor, writer, second_writer):
        a = assigned(editor, writer)
        assert reassign(auth_client(editor), a, second_writer.pk, deadline="next week").status_code == 400
        a.refresh_from_db()
        assert a.writer == writer

    def test_only_an_editor_can_reassign(self, auth_client, editor, writer, second_writer):
        a = assigned(editor, writer)
        assert reassign(auth_client(writer), a, second_writer.pk).status_code == 403
