"""UC-4.3 Subscribe to BOSS Magazine.

PayRex is never called: its checkout API is replaced by a stand-in, and its
notifications are built and signed here exactly as PayRex signs them."""
import json
from datetime import timedelta

import httpx
import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.accounts.models import ReaderProfile, User
from apps.content.entitlement import is_entitled
from apps.notifications.models import Notification
from apps.payments import payrex
from apps.payments.management.commands.simulate_payment import paid_event
from apps.payments.models import Subscription, Transaction
from apps.payments.plans import ANNUAL, MONTHLY


@pytest.fixture(autouse=True)
def payrex_keys(settings):
    settings.PAYREX_SECRET_KEY = "sk_test_novus"
    settings.PAYREX_WEBHOOK_SECRET = "whsk_test_novus"
    settings.FRONTEND_URL = "https://novus.test"
    cache.clear()


@pytest.fixture
def reader(make_user):
    return make_user("ana@example.com", User.Role.READER)


@pytest.fixture
def admin(make_user):
    return make_user("admin@boss.ph", User.Role.ADMIN)


def deliver(event, signature=None):
    body = json.dumps(event).encode()
    return Client().post("/api/payments/webhook/", body, content_type="application/json",
                         HTTP_PAYREX_SIGNATURE=signature if signature is not None
                         else payrex.sign(body))


def pay(reader, plan=MONTHLY, **kw):
    kw.setdefault("pay_id", None)
    r = deliver(paid_event(reader, plan, kw.pop("reference", "NVS-REF"), **kw))
    assert r.status_code == 200, r.content
    return r.json()["outcome"]


class FakePayRex:
    """Stands in for PayRex's server, behind a real httpx request, so the
    request is built and encoded exactly as it would be for PayRex."""

    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def __call__(self, request):
        from urllib.parse import parse_qsl
        body = parse_qsl(request.read().decode(), keep_blank_values=True)
        self.sent.append((str(request.url), body, request.headers))
        if self.fail:
            return httpx.Response(400, json={"errors": [{"detail": "bad"}]})
        return httpx.Response(200, json={"id": "cs_123", "resource": "checkout_session",
                                         "url": "https://checkout.payrexhq.com/c/cs_123",
                                         "status": "active"})


def use_fake(monkeypatch, fake):
    """Route httpx.post through a real client whose network is the fake."""
    real_post = httpx.post

    def post(url, **kw):
        with httpx.Client(transport=httpx.MockTransport(fake)) as client:
            return client.post(url, **kw)
    monkeypatch.setattr("apps.payments.payrex.httpx.post", post)
    assert real_post is not post
    return fake


def test_the_webhook_command_sends_a_valid_request(settings, monkeypatch, capsys):
    from django.core.management import call_command
    settings.PAYREX_SECRET_KEY = "sk_test_novus"
    sent = []

    def fake(request):
        from urllib.parse import parse_qsl
        sent.append(parse_qsl(request.read().decode()))
        return httpx.Response(200, json={"id": "wh_1", "secret_key": "whsk_new"})
    use_fake(monkeypatch, fake)
    call_command("payrex_webhook", "https://novus.example/api/payments/webhook/")
    assert ("events[]", "payment_intent.succeeded") in sent[0]
    assert ("url", "https://novus.example/api/payments/webhook/") in sent[0]
    assert "PAYREX_WEBHOOK_SECRET=whsk_new" in capsys.readouterr().out


@pytest.mark.django_db
class TestPlansAndCheckout:
    def test_the_plans_and_prices_are_listed(self):                  # step 1.1
        r = Client().get("/api/payments/plans/").json()
        assert [(p["code"], p["price"]) for p in r["plans"]] == [("MONTHLY", "₱199"), ("ANNUAL", "₱1,990")]
        assert r["available"] is True

    def test_continue_opens_a_payrex_checkout(self, auth_client, reader, monkeypatch):  # step 2.1
        fake = use_fake(monkeypatch, FakePayRex())
        r = auth_client(reader).post("/api/payments/checkout/", {"plan": "ANNUAL"}, format="json")
        assert r.status_code == 200
        assert r.data["checkout_url"] == "https://checkout.payrexhq.com/c/cs_123"
        url, form, headers = fake.sent[0]
        assert url == "https://api.payrexhq.com/checkout_sessions"
        assert headers["content-type"] == "application/x-www-form-urlencoded"
        import base64
        assert headers["authorization"] == "Basic " + base64.b64encode(b"sk_test_novus:").decode()
        ref = r.data["reference"]
        for field in [("currency", "PHP"), ("line_items[][amount]", "199000"),
                      ("line_items[][quantity]", "1"), ("payment_methods[]", "gcash"),
                      ("payment_methods[]", "maya"), ("metadata[reader_id]", str(reader.pk)),
                      ("metadata[plan]", "ANNUAL"), ("metadata[reference]", ref),
                      ("customer_reference_id", ref),
                      ("success_url", f"https://novus.test/subscribe/return?ref={ref}"),
                      ("cancel_url", "https://novus.test/subscribe?cancelled=1")]:
            assert field in form, field

    def test_nested_values_are_sent_the_way_payrex_reads_them(self):
        assert payrex.form({"a": 1, "m": {"k": "v"}, "pm": ["gcash", "card"],
                            "li": [{"name": "x", "amount": 2}]}) == [
            ("a", "1"), ("m[k]", "v"), ("pm[]", "gcash"), ("pm[]", "card"),
            ("li[][name]", "x"), ("li[][amount]", "2")]

    def test_an_abandoned_checkout_records_nothing(self, auth_client, reader, monkeypatch):  # A1
        use_fake(monkeypatch, FakePayRex())
        auth_client(reader).post("/api/payments/checkout/", {"plan": "MONTHLY"}, format="json")
        assert not Transaction.objects.exists() and not Subscription.objects.exists()
        assert not is_entitled(reader)

    def test_refusals(self, auth_client, reader, make_user, settings, monkeypatch):
        c = auth_client(reader)
        assert c.post("/api/payments/checkout/", {"plan": "WEEKLY"}, format="json").status_code == 400
        use_fake(monkeypatch, FakePayRex(fail=True))
        assert c.post("/api/payments/checkout/", {"plan": "MONTHLY"}, format="json").status_code == 502
        settings.PAYREX_WEBHOOK_SECRET = ""      # no way to trust the confirmation
        assert c.post("/api/payments/checkout/", {"plan": "MONTHLY"}, format="json").status_code == 503
        assert Client().get("/api/payments/plans/").json()["available"] is False
        editor = make_user("ed@boss.ph", User.Role.EDITOR)
        assert auth_client(editor).post("/api/payments/checkout/", {"plan": "MONTHLY"},
                                        format="json").status_code == 403


@pytest.mark.django_db
class TestPaymentNotification:
    def test_a_paid_checkout_makes_the_reader_a_subscriber(self, reader):   # steps 3.1 to 3.4
        assert pay(reader, MONTHLY, pay_id="pay_1") == "granted"
        tx = Transaction.objects.get()
        assert (tx.status, tx.amount_cents, tx.payment_method) == ("SUCCEEDED", 19_900, "gcash")
        assert tx.provider_transaction_id == "pay_1"
        sub = tx.subscription
        assert sub.status == "ACTIVE"
        assert abs((sub.current_period_end - timezone.now()) - timedelta(days=30)) < timedelta(minutes=1)
        reader.refresh_from_db()
        assert reader.reader_profile.tier == ReaderProfile.Tier.SUBSCRIBER
        assert reader.reader_profile.subscription_renews_at == sub.current_period_end
        assert is_entitled(reader)
        assert Notification.objects.filter(recipient=reader, kind="SUBSCRIPTION").exists()

    def test_annual_buys_a_year(self, reader):
        pay(reader, ANNUAL)
        sub = Subscription.objects.get()
        assert (sub.current_period_end - sub.current_period_start).days == 365

    def test_a_repeated_notification_is_ignored(self, reader):                 # E1 duplicate
        event = paid_event(reader, MONTHLY, "NVS-1", pay_id="pay_same")
        assert deliver(event).json()["outcome"] == "granted"
        end = Subscription.objects.get().current_period_end
        assert deliver(event).json()["outcome"] == "duplicate"
        assert Transaction.objects.count() == 1
        assert Subscription.objects.get().current_period_end == end

    def test_a_forged_notification_grants_nothing_and_alerts_an_admin(self, reader, admin):  # E1
        event = paid_event(reader, MONTHLY, "NVS-1")
        assert deliver(event, signature="t=1,te=forged,li=").status_code == 400
        assert deliver(event, signature="").status_code == 400
        assert not Transaction.objects.exists() and not is_entitled(reader)
        alerts = Notification.objects.filter(recipient=admin, kind="PAYMENT_ALERT")
        assert alerts.count() == 1                # throttled, not one per request

    def test_a_live_signature_is_checked_too(self, reader):
        import hashlib
        import hmac
        body = json.dumps(paid_event(reader, MONTHLY, "NVS-1")).encode()
        digest = hmac.new(b"whsk_test_novus", b"99." + body, hashlib.sha256).hexdigest()
        r = Client().post("/api/payments/webhook/", body, content_type="application/json",
                          HTTP_PAYREX_SIGNATURE=f"t=99,te=,li={digest}")
        assert r.status_code == 200

    def test_a_tampered_body_fails_the_signature(self, reader):
        body = json.dumps(paid_event(reader, MONTHLY, "NVS-1")).encode()
        sig = payrex.sign(body)
        tampered = body.replace(b'"MONTHLY"', b'"ANNUAL"')
        r = Client().post("/api/payments/webhook/", tampered, content_type="application/json",
                          HTTP_PAYREX_SIGNATURE=sig)
        assert r.status_code == 400 and not Transaction.objects.exists()

    def test_the_amount_received_is_what_counts(self, reader, admin):
        event = paid_event(reader, MONTHLY, "NVS-1")
        event["data"]["resource"]["amount_received"] = 2_000
        assert deliver(event).json()["outcome"] == "not_granted"
        assert Transaction.objects.get().failure_code == "amount_mismatch"
        assert not is_entitled(reader)

    def test_the_method_is_recorded_when_payrex_says(self, reader):
        event = paid_event(reader, MONTHLY, "NVS-1", method="maya")
        event["data"]["resource"]["payment_methods"] = ["gcash", "maya", "card", "qrph"]
        event["data"]["resource"]["latest_payment"] = {"payment_method": {"type": "maya"}}
        deliver(event)
        assert Transaction.objects.get().payment_method == "maya"

    def test_an_unfinished_payment_grants_nothing(self, reader):                 # E2
        assert pay(reader, MONTHLY, status="awaiting_payment_method") == "not_granted"
        assert Transaction.objects.get().status == "FAILED"
        assert not Subscription.objects.exists() and not is_entitled(reader)

    def test_the_wrong_amount_grants_nothing_and_alerts(self, reader, admin):
        assert pay(reader, ANNUAL, amount=19_900) == "not_granted"
        assert Transaction.objects.get().failure_code == "amount_mismatch"
        assert not is_entitled(reader)
        assert Notification.objects.filter(recipient=admin, kind="PAYMENT_ALERT").exists()

    def test_an_unknown_reader_grants_nothing_and_alerts(self, make_user, admin):
        editor = make_user("ed@boss.ph", User.Role.EDITOR)
        assert pay(editor, MONTHLY) == "unmatched"
        assert not Transaction.objects.exists()
        assert Notification.objects.filter(recipient=admin, kind="PAYMENT_ALERT").exists()

    def test_other_events_are_acknowledged_and_ignored(self, reader):
        event = paid_event(reader, MONTHLY, "NVS-1")
        event["type"] = "refund.created"
        r = deliver(event)
        assert r.status_code == 200 and r.json()["outcome"] == "ignored"

    def test_it_still_works_in_maintenance_mode(self, reader):
        from apps.platform.models import PlatformSetting
        s = PlatformSetting.load() if hasattr(PlatformSetting, "load") else PlatformSetting.objects.get_or_create(pk=1)[0]
        s.maintenance_mode = True
        s.save()
        assert pay(reader, MONTHLY) == "granted"


@pytest.mark.django_db
class TestRenewalAndAccess:
    def test_renewing_early_adds_to_the_end(self, reader):
        pay(reader, MONTHLY)
        first_end = Subscription.objects.get().current_period_end
        pay(reader, ANNUAL)
        sub = Subscription.objects.get()
        assert sub.current_period_end == first_end + timedelta(days=365)
        assert sub.plan == "ANNUAL" and Transaction.objects.count() == 2

    def test_paying_again_undoes_a_cancellation(self, reader):
        pay(reader, MONTHLY)
        Subscription.objects.update(status="CANCELLED", cancel_at_period_end=True,
                                    cancelled_at=timezone.now())
        pay(reader, MONTHLY)
        sub = Subscription.objects.get()
        assert sub.status == "ACTIVE" and not sub.cancel_at_period_end and sub.cancelled_at is None

    def test_access_ends_on_the_paid_up_date(self, reader):
        pay(reader, MONTHLY)
        ReaderProfile.objects.filter(user=reader).update(
            subscription_renews_at=timezone.now() - timedelta(seconds=1))
        reader.refresh_from_db()
        assert not is_entitled(reader)

    def test_an_admin_granted_subscription_has_no_end(self, reader):
        ReaderProfile.objects.filter(user=reader).update(tier="SUBSCRIBER", subscription_renews_at=None)
        reader.refresh_from_db()
        assert is_entitled(reader)

    def test_an_expired_subscriber_is_not_sent_new_issue_notices(self, reader):
        from apps.publishing.services import subscribers
        ReaderProfile.objects.filter(user=reader).update(
            tier="SUBSCRIBER", subscription_renews_at=timezone.now() - timedelta(days=1))
        assert reader not in subscribers()


@pytest.mark.django_db
class TestReturnPage:
    def test_it_reports_pending_then_paid(self, auth_client, reader):          # step 4.1
        c = auth_client(reader)
        assert c.get("/api/payments/checkout/NVS-9/").data["status"] == "pending"
        pay(reader, MONTHLY, reference="NVS-9")
        r = c.get("/api/payments/checkout/NVS-9/").data
        assert r["status"] == "paid" and r["entitled"] is True

    def test_it_reports_a_decline(self, auth_client, reader):
        pay(reader, MONTHLY, reference="NVS-8", status="canceled")
        assert auth_client(reader).get("/api/payments/checkout/NVS-8/").data["status"] == "failed"

    def test_another_reader_cannot_see_it(self, auth_client, reader, make_user):
        pay(reader, MONTHLY, reference="NVS-7")
        other = make_user("ben@example.com", User.Role.READER)
        assert auth_client(other).get("/api/payments/checkout/NVS-7/").data["status"] == "pending"
