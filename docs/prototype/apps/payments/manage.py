"""
UC-4.4 Manage a Subscription, and the daily upkeep that ends subscriptions
on their paid-up date.

Subscriptions are prepaid, so cancelling charges nothing and refunds
nothing: it stops the renewal reminders and records that the reader does not
mean to continue. Access lasts to the end of the period already paid for
(BR-11, RA 7394).
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ReaderProfile
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Subscription, Transaction
from .plans import PLANS
from .services import long_date

REMIND_BEFORE = timedelta(days=3)
METHOD_NAMES = {"gcash": "GCash", "paymaya": "Maya", "card": "Card", "qrph": "QR Ph",
                "grab_pay": "GrabPay", "billease": "BillEase", "dob": "Online banking"}


def method_name(code):
    return METHOD_NAMES.get(code, code.replace("_", " ").title()) if code else ""


def current(reader, now=None):
    """The subscription still giving access, if any."""
    now = now or timezone.now()
    return (Subscription.objects
            .filter(reader=reader, current_period_end__gt=now,
                    status__in=[Subscription.Status.ACTIVE, Subscription.Status.CANCELLED])
            .order_by("-current_period_end").first())


def summary(reader):
    """What the Subscription page shows (UC-4.4 step 1.1)."""
    sub = current(reader)
    paid = Transaction.objects.filter(reader=reader)
    last = paid.filter(status=Transaction.Status.SUCCEEDED).first()
    profile = ReaderProfile.objects.filter(user=reader).first()
    granted = bool(sub is None and profile and profile.tier == ReaderProfile.Tier.SUBSCRIBER
                   and profile.subscription_renews_at is None)
    return {
        "subscription": sub and {
            "plan": sub.plan, "plan_name": PLANS[sub.plan].name, "status": sub.status,
            "access_until": sub.current_period_end, "cancelled_at": sub.cancelled_at,
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
        "granted_by_staff": granted,
        "payment_method": method_name(last.payment_method) if last else "",
        "history": [{
            "date": t.occurred_at, "plan": PLANS[t.plan].name if t.plan in PLANS else t.plan,
            "amount": f"₱{t.amount_cents / 100:,.2f}", "method": method_name(t.payment_method),
            "status": t.get_status_display(),
        } for t in paid[:12]],
    }


def cancel(reader):
    """UC-4.4 steps 3 and 4: end the subscription at the close of the paid
    period. Returns the subscription, or None if there is nothing to cancel."""
    now = timezone.now()
    with transaction.atomic():
        sub = (Subscription.objects.select_for_update()
               .filter(reader=reader, status=Subscription.Status.ACTIVE, current_period_end__gt=now)
               .first())
        if sub is None:
            return None
        sub.status = Subscription.Status.CANCELLED
        sub.cancel_at_period_end = True
        sub.cancelled_at = now
        sub.save()
    notify(reader, Notification.Kind.SUBSCRIPTION,
           f"Your subscription is cancelled. You can still read everything until "
           f"{long_date(sub.current_period_end)}.", "/subscription")
    return sub


def upkeep(now=None):
    """Run daily. Ends subscriptions that reached their paid-up date and
    reminds readers whose access ends within three days. Safe to run more
    than once a day: each reminder and each ending happens once."""
    now = now or timezone.now()
    ended = reminded = 0

    for sub in Subscription.objects.filter(
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.CANCELLED],
            current_period_end__lte=now).select_related("reader"):
        with transaction.atomic():
            sub.status = Subscription.Status.EXPIRED
            sub.save(update_fields=["status", "updated_at"])
            ReaderProfile.objects.filter(
                user=sub.reader, tier=ReaderProfile.Tier.SUBSCRIBER,
                subscription_renews_at__lte=now,
            ).update(tier=ReaderProfile.Tier.FREE)
        notify(sub.reader, Notification.Kind.SUBSCRIPTION,
               "Your subscription has ended. You can subscribe again at any time.", "/subscribe")
        ended += 1

    for sub in Subscription.objects.filter(
            status=Subscription.Status.ACTIVE, reminder_sent_at__isnull=True,
            current_period_end__gt=now, current_period_end__lte=now + REMIND_BEFORE,
    ).select_related("reader"):
        sub.reminder_sent_at = now
        sub.save(update_fields=["reminder_sent_at", "updated_at"])
        notify(sub.reader, Notification.Kind.SUBSCRIPTION,
               f"Your subscription ends on {long_date(sub.current_period_end)}. "
               "Renew to keep reading.", "/subscribe")
        reminded += 1

    return ended, reminded
