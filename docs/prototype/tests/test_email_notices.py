"""Email notices (UC-5.2 preferences, UC-2.5 step 3).

A notice is shown in the app and, for anyone who turned email on, sent by
email too. Publishing an issue tells its subscribers."""
import httpx
import pytest
from django.core import mail
from django.core.files.base import ContentFile

from apps.accounts.models import ReaderProfile, User
from apps.editorial.models import Article
from apps.notifications.models import EmailDispatch, Notification, NotificationPreference
from apps.notifications.services import notify


def prefs(user, **kw):
    NotificationPreference.objects.update_or_create(user=user, defaults=kw)
    return User.objects.select_related("notification_preference").get(pk=user.pk)


def subscriber(make_user, address, **pref):
    u = make_user(address, User.Role.READER)
    ReaderProfile.objects.filter(user=u).update(tier=ReaderProfile.Tier.SUBSCRIBER)
    return prefs(u, **pref) if pref else u


@pytest.fixture
def ready_issue(writer, publisher, make_user):
    from apps.design.models import MagazineDesign
    from apps.issues.models import Issue
    issue = Issue.objects.create(number=90, title="Business Leaders",
                                 minimum_articles=1, created_by=publisher)
    Article.objects.create(writer=writer, title="Ready copy", body="<p>Final.</p>",
                           category="Tech", status=Article.Status.APPROVED, issue=issue)
    d = MagazineDesign.objects.create(issue=issue, version="v1.0",
                                      designer=make_user("d90@boss.ph", User.Role.GRAPHIC_DESIGNER),
                                      status=MagazineDesign.Status.APPROVED)
    d.file.save("layout.pdf", ContentFile(b"%PDF-1.4"), save=True)
    return issue


def publish(auth_client, publisher, issue, capture):
    c = auth_client(publisher)
    c.post(f"/api/publication/issues/{issue.id}/close/")
    with capture(execute=True):
        r = c.post(f"/api/publication/issues/{issue.id}/publish/")
    assert r.status_code == 200, r.data


@pytest.mark.django_db
class TestNewIssueNotice:
    def test_subscribers_are_told_and_emailed_if_they_asked(
        self, auth_client, publisher, make_user, ready_issue, django_capture_on_commit_callbacks
    ):
        wants_email = subscriber(make_user, "sub1@example.com", email=True)
        app_only = subscriber(make_user, "sub2@example.com")
        publish(auth_client, publisher, ready_issue, django_capture_on_commit_callbacks)

        for u in (wants_email, app_only):
            n = Notification.objects.get(recipient=u, kind=Notification.Kind.NEW_ISSUE)
            assert n.link == f"/issues/{ready_issue.pk}"
        assert [m.to for m in mail.outbox] == [["sub1@example.com"]]
        body = mail.outbox[0].body
        assert f"/issues/{ready_issue.pk}" in body and "/account" in body
        assert EmailDispatch.objects.get(recipient=wants_email).status == EmailDispatch.Status.SENT

    def test_free_suspended_and_muted_readers_are_not(
        self, auth_client, publisher, make_user, ready_issue, django_capture_on_commit_callbacks
    ):
        free = prefs(make_user("free@example.com", User.Role.READER), email=True)
        gone = subscriber(make_user, "gone@example.com", email=True)
        User.objects.filter(pk=gone.pk).update(is_suspended=True)
        muted = subscriber(make_user, "muted@example.com", email=True,
                           muted_kinds=[Notification.Kind.NEW_ISSUE])
        publish(auth_client, publisher, ready_issue, django_capture_on_commit_callbacks)

        assert not Notification.objects.filter(
            kind=Notification.Kind.NEW_ISSUE, recipient__in=[free, gone, muted]).exists()
        assert mail.outbox == []

    def test_nothing_is_emailed_if_publishing_fails(
        self, auth_client, publisher, make_user, ready_issue, django_capture_on_commit_callbacks
    ):
        subscriber(make_user, "sub@example.com", email=True)
        ready_issue.articles.update(status=Article.Status.UNDER_REVIEW)   # not ready
        c = auth_client(publisher)
        with django_capture_on_commit_callbacks(execute=True):
            r = c.post(f"/api/publication/issues/{ready_issue.id}/publish/")
        assert r.status_code != 200
        assert mail.outbox == [] and not EmailDispatch.objects.exists()


@pytest.mark.django_db
class TestEmailPreference:
    def test_staff_who_turned_email_on_get_their_notices_by_email(
        self, editor, writer, django_capture_on_commit_callbacks
    ):
        w = prefs(writer, email=True)
        with django_capture_on_commit_callbacks(execute=True):
            notify(w, Notification.Kind.ASSIGNED, 'You have been assigned "Ports".', "/writer/compose/1")
        assert Notification.objects.filter(recipient=w).count() == 1
        assert mail.outbox[0].to == [w.email]
        assert "/notifications" in mail.outbox[0].body
        assert "Article assigned" in mail.outbox[0].subject

    def test_email_is_off_by_default(self, writer, django_capture_on_commit_callbacks):
        w = prefs(writer)
        with django_capture_on_commit_callbacks(execute=True):
            notify(w, Notification.Kind.ASSIGNED, "x", "/writer")
        assert mail.outbox == []

    def test_email_can_come_without_the_in_app_notice(self, writer, django_capture_on_commit_callbacks):
        w = prefs(writer, in_app=False, email=True)
        with django_capture_on_commit_callbacks(execute=True):
            assert notify(w, Notification.Kind.MESSAGE, "x", "/writer") is None
        assert len(mail.outbox) == 1 and not Notification.objects.filter(recipient=w).exists()

    def test_the_preference_can_be_saved(self, auth_client, writer):
        r = auth_client(writer).patch("/api/notifications/preferences/", {"email": True}, format="json")
        assert r.status_code == 200 and r.data["email"] is True


class FakeResend:
    """Records what the backend sends instead of calling Resend."""
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def __call__(self, client, url, json=None, headers=None):
        self.calls.append((url, json))
        if self.fail:
            raise httpx.ConnectError("no network")
        if url.endswith("/batch"):
            return httpx.Response(200, json={"data": [{"id": f"m{i}"} for i in range(len(json))]})
        return httpx.Response(200, json={"id": "m0"})


@pytest.mark.django_db
class TestResendBatching:
    @pytest.fixture
    def resend(self, settings, monkeypatch):
        settings.EMAIL_BACKEND = "apps.notifications.backends.ResendEmailBackend"
        settings.RESEND_API_KEY = "re_test"
        def use(fake):
            monkeypatch.setattr("apps.notifications.backends.httpx.Client.post",
                                lambda client, url, json=None, headers=None: fake(client, url, json, headers))
            return fake
        return use

    def _send(self, make_user, n):
        from apps.notifications.email import send_many
        users = [make_user(f"r{i}@example.com", User.Role.READER) for i in range(n)]
        return send_many([(u, {"message": "m", "url": "u", "settings_url": "s"}, None) for u in users],
                         "notification", "Subject")

    def test_many_messages_go_in_one_batch_call(self, make_user, resend):
        fake = resend(FakeResend())
        sent = self._send(make_user, 3)
        assert len(fake.calls) == 1 and fake.calls[0][0].endswith("/emails/batch")
        assert [d.provider_message_id for d in sent] == ["m0", "m1", "m2"]
        assert all(d.status == EmailDispatch.Status.SENT for d in sent)

    def test_over_a_hundred_are_split(self, make_user, resend):
        fake = resend(FakeResend())
        self._send(make_user, 101)
        assert [len(j) if isinstance(j, list) else 1 for _, j in fake.calls] == [100, 1]

    def test_a_failed_batch_is_recorded_on_each_message(self, make_user, resend):
        resend(FakeResend(fail=True))
        sent = self._send(make_user, 2)
        assert all(d.status == EmailDispatch.Status.FAILED and "no network" in d.last_error
                   for d in sent)
