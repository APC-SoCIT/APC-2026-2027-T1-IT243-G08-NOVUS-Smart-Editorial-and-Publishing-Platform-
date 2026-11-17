"""UC-4.4 Manage a Subscription, the daily upkeep that ends subscriptions on
their paid-up date, and the revenue report (UC-3.1)."""
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.accounts.models import ReaderProfile, User
from apps.content.entitlement import is_entitled
from apps.notifications.models import Notification
from apps.payments.manage import upkeep
from apps.payments.models import Subscription
from apps.payments.plans import ANNUAL, MONTHLY
from tests.test_subscribe import pay


@pytest.fixture(autouse=True)
def payrex_keys(settings):
    settings.PAYREX_SECRET_KEY = "sk_test_novus"
    settings.PAYREX_WEBHOOK_SECRET = "whsk_test_novus"
    cache.clear()


@pytest.fixture
def reader(make_user):
    return make_user("ana@example.com", User.Role.READER)


def fresh(user):
    return User.objects.select_related("reader_profile").get(pk=user.pk)


def move_end(reader, when):
    Subscription.objects.filter(reader=reader).update(current_period_end=when)
    ReaderProfile.objects.filter(user=reader).update(subscription_renews_at=when)


@pytest.mark.django_db
class TestSubscriptionPage:
    def test_it_shows_the_plan_date_and_payment_method(self, auth_client, reader):   # step 1.1
        pay(reader, ANNUAL, pay_id="pay_a")
        r = auth_client(reader).get("/api/payments/subscription/").data
        assert r["subscription"]["plan_name"] == "Annual"
        assert r["subscription"]["status"] == "ACTIVE"
        assert r["payment_method"] == "GCash"
        assert [(h["amount"], h["status"]) for h in r["history"]] == [("₱1,990.00", "Succeeded")]

    def test_a_free_reader_has_none(self, auth_client, reader):
        r = auth_client(reader).get("/api/payments/subscription/").data
        assert r["subscription"] is None and r["granted_by_staff"] is False

    def test_a_staff_granted_subscription_is_labelled(self, auth_client, reader):
        ReaderProfile.objects.filter(user=reader).update(tier="SUBSCRIBER", subscription_renews_at=None)
        assert auth_client(reader).get("/api/payments/subscription/").data["granted_by_staff"] is True


@pytest.mark.django_db
class TestCancel:
    def test_access_continues_to_the_end_of_the_paid_period(self, auth_client, reader):  # steps 2 to 4
        pay(reader, MONTHLY)
        r = auth_client(reader).post("/api/payments/subscription/cancel/")
        assert r.status_code == 200 and r.data["subscription"]["status"] == "CANCELLED"
        sub = Subscription.objects.get()
        assert sub.cancel_at_period_end and sub.cancelled_at
        assert is_entitled(fresh(reader))
        assert Notification.objects.filter(recipient=reader, message__contains="still read").exists()

    def test_nothing_to_cancel(self, auth_client, reader):
        c = auth_client(reader)
        assert c.post("/api/payments/subscription/cancel/").status_code == 409
        pay(reader, MONTHLY)
        c.post("/api/payments/subscription/cancel/")
        assert c.post("/api/payments/subscription/cancel/").status_code == 409


@pytest.mark.django_db
class TestUpkeep:
    def test_a_lapsed_subscription_returns_the_reader_to_free(self, reader):        # step 4.1
        pay(reader, MONTHLY)
        move_end(reader, timezone.now() - timedelta(minutes=1))
        assert upkeep() == (1, 0)
        assert Subscription.objects.get().status == "EXPIRED"
        assert fresh(reader).reader_profile.tier == ReaderProfile.Tier.FREE
        assert Notification.objects.filter(recipient=reader, message__contains="has ended").exists()
        assert upkeep() == (0, 0)                    # once only

    def test_a_cancelled_one_ends_the_same_way(self, auth_client, reader):
        pay(reader, MONTHLY)
        auth_client(reader).post("/api/payments/subscription/cancel/")
        move_end(reader, timezone.now() - timedelta(minutes=1))
        upkeep()
        assert fresh(reader).reader_profile.tier == ReaderProfile.Tier.FREE

    def test_a_reminder_goes_out_once_three_days_before(self, reader):
        pay(reader, MONTHLY)
        move_end(reader, timezone.now() + timedelta(days=2))
        assert upkeep() == (0, 1)
        assert upkeep() == (0, 0)
        assert Notification.objects.filter(recipient=reader, message__contains="Renew").count() == 1

    def test_no_reminder_after_cancelling(self, auth_client, reader):
        pay(reader, MONTHLY)
        auth_client(reader).post("/api/payments/subscription/cancel/")
        move_end(reader, timezone.now() + timedelta(days=2))
        assert upkeep() == (0, 0)

    def test_renewing_after_a_reminder_rearms_it(self, reader):
        pay(reader, MONTHLY)
        move_end(reader, timezone.now() + timedelta(days=2))
        upkeep()
        pay(reader, MONTHLY)
        assert Subscription.objects.get().reminder_sent_at is None

    def test_the_daily_sweep_runs_it(self, settings, reader):
        settings.SCHEDULER_TOKEN = "tok"
        pay(reader, MONTHLY)
        move_end(reader, timezone.now() - timedelta(minutes=1))
        r = Client().post("/api/scheduler/check-deadlines/", HTTP_X_SCHEDULER_TOKEN="tok")
        assert r.status_code == 200 and "Subscriptions ended: 1" in r.json()["output"]


@pytest.mark.django_db
class TestRevenueReport:
    def test_the_publisher_sees_confirmed_revenue(self, auth_client, publisher, reader, make_user):
        pay(reader, ANNUAL)
        pay(make_user("ben@example.com", User.Role.READER), MONTHLY)
        pay(make_user("cy@example.com", User.Role.READER), MONTHLY, status="canceled")
        r = auth_client(publisher).get("/api/reports/revenue/?days=30").data
        assert r["revenue_cents"] == 199_000 + 19_900
        assert (r["payments"], r["failed_payments"]) == (2, 1)
        assert r["by_plan"]["ANNUAL"]["revenue_cents"] == 199_000

    def test_an_editor_is_refused(self, auth_client, editor):                       # UC-3.1 E1
        r = auth_client(editor).get("/api/reports/revenue/")
        assert r.status_code == 403
        assert "publisher and administrators" in r.data["detail"]
