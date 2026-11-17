"""
What a verified PayMongo notification does (UC-4.3 steps 3.2 to 3.4).

record_checkout_payment() is the only place access is granted for money.
It is safe to call twice with the same notification: the payment's PayMongo
id is a unique key, so the second call finds it recorded and does nothing.
"""
import logging
import secrets
from datetime import datetime, timezone as dt_timezone

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import ReaderProfile, User
from apps.notifications.models import Notification
from apps.notifications.services import notify, notify_many

from .models import Subscription, Transaction
from .plans import CURRENCY, PLANS

log = logging.getLogger(__name__)


def new_reference(reader):
    return f"NVS-{reader.pk}-{secrets.token_hex(4).upper()}"


def alert_admins(reason, message):
    """UC-4.3 E1: tell administrators about a notification that cannot be
    trusted or matched. At most one alert per reason every ten minutes, so a
    flood of forged requests cannot flood the administrators too."""
    log.warning("Payment alert (%s): %s", reason, message)
    if not cache.add(f"payments:alert:{reason}", 1, timeout=600):
        return
    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    notify_many(admins, Notification.Kind.PAYMENT_ALERT, message, "/admin/payments/transaction/")


def _when(timestamp):
    try:
        return datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return timezone.now()


def _method(session, payment):
    used = session.get("payment_method_used") or ""
    source = payment.get("source") or {}
    return (used or source.get("type") or "")[:30]


def record_checkout_payment(event):
    """Handle checkout_session.payment.paid. Returns a short outcome word."""
    session_obj = event["data"]["attributes"]["data"]
    session = session_obj.get("attributes") or {}
    meta = session.get("metadata") or {}
    payments = session.get("payments") or []
    if not payments:
        return "no_payment"

    # A checkout keeps every attempt (a declined card, then GCash); at most
    # one of them is paid.
    payment = next((p for p in payments if (p.get("attributes") or {}).get("status") == "paid"),
                   payments[-1])
    pay = payment.get("attributes") or {}
    pay_id = payment.get("id", "")
    if Transaction.objects.filter(provider_transaction_id=pay_id).exists():
        return "duplicate"

    reader = User.objects.filter(pk=meta.get("reader_id"), role=User.Role.READER).first()
    plan = PLANS.get(meta.get("plan"))
    if reader is None or plan is None or not pay_id:
        alert_admins("unmatched", f"A PayMongo payment ({pay_id or 'no id'}) could not be "
                                  "matched to a reader and plan. Nothing was granted.")
        return "unmatched"

    amount = pay.get("amount")
    if amount is None:      # some PayMongo test events leave it out
        amount = sum(int(li.get("amount", 0)) * int(li.get("quantity", 1))
                     for li in session.get("line_items") or [])
    currency = (pay.get("currency") or CURRENCY).upper()
    failure = ""
    if pay.get("status") != "paid":                       # UC-4.3 E2
        failure = (pay.get("failed_code") or pay.get("status") or "not_paid")[:50]
    elif amount != plan.amount or currency != CURRENCY:
        failure = "amount_mismatch"

    now = timezone.now()
    try:
        with transaction.atomic():
            tx = Transaction.objects.create(
                reader=reader, provider_transaction_id=pay_id,
                reference=(meta.get("reference") or session.get("reference_number") or "")[:40],
                status=Transaction.Status.FAILED if failure else Transaction.Status.SUCCEEDED,
                plan=plan.code, amount_cents=amount or 0, currency=currency[:3],
                payment_method=_method(session, pay), failure_code=failure,
                raw_payload=event, occurred_at=_when(pay.get("paid_at")) if not failure else now,
            )
            if not failure:
                tx.subscription = grant(reader, plan, now)
                tx.save(update_fields=["subscription", "updated_at"])
    except IntegrityError:
        # The same notification arriving twice at the same moment.
        return "duplicate"

    if failure == "amount_mismatch":
        alert_admins("amount", f"PayMongo payment {pay_id} was for {amount} {currency}, "
                               f"not the {plan.name} price. Nothing was granted.")
    if failure:
        return "not_granted"

    notify(reader, Notification.Kind.SUBSCRIPTION,
           f"Thank you for subscribing. You can read everything until "
           f"{long_date(tx.subscription.current_period_end)}.", "/issues")
    return "granted"


def long_date(moment):
    d = timezone.localtime(moment)
    return f"{d:%B} {d.day}, {d.year}"


def grant(reader, plan, now):
    """Give the reader the plan's period of access.

    A reader who still has time left gets the new period added to the end of
    it, so renewing early never loses days. Paying again also undoes a
    cancellation.
    """
    sub = (Subscription.objects.select_for_update()
           .filter(reader=reader, current_period_end__gt=now,
                   status__in=[Subscription.Status.ACTIVE, Subscription.Status.CANCELLED])
           .order_by("-current_period_end").first())
    if sub:
        sub.current_period_end += plan.length
        sub.plan = plan.code
        sub.status = Subscription.Status.ACTIVE
        sub.cancel_at_period_end = False
        sub.cancelled_at = None
        sub.reminder_sent_at = None
        sub.save()
    else:
        sub = Subscription.objects.create(
            reader=reader, plan=plan.code, status=Subscription.Status.ACTIVE,
            provider_subscription_id=f"novus-{secrets.token_hex(12)}",
            current_period_start=now, current_period_end=now + plan.length,
        )

    profile, _ = ReaderProfile.objects.select_for_update().get_or_create(user=reader)
    if profile.tier != ReaderProfile.Tier.SUBSCRIBER or not profile.subscription_renews_at \
            or profile.subscription_renews_at <= now:
        profile.subscription_started_at = now
    profile.tier = ReaderProfile.Tier.SUBSCRIBER
    profile.subscription_renews_at = sub.current_period_end
    profile.save()
    return sub
