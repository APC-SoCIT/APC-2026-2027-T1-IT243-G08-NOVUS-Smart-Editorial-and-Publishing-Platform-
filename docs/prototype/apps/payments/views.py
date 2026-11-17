"""
UC-4.3 Subscribe to BOSS Magazine.

  GET  plans/                 the plans and prices (step 1.1)
  POST checkout/              open a PayMongo checkout for a plan (step 2.1)
  GET  checkout/<reference>/  what became of it, for the return page (step 4.1)
  POST webhook/               PayMongo's signed notification (steps 3.1 to 3.4)
"""
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.content.entitlement import is_entitled

from . import paymongo, services
from .models import Transaction
from .plans import PLANS

log = logging.getLogger(__name__)


class CheckoutRateThrottle(UserRateThrottle):
    scope = "checkout"


class PlanListView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"plans": [p.as_dict() for p in PLANS.values()],
                         "available": paymongo.configured()})


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [CheckoutRateThrottle]

    def post(self, request):
        user = request.user
        if user.role != user.Role.READER:
            return Response({"detail": "Staff accounts already have full access."},
                            status=status.HTTP_403_FORBIDDEN)
        plan = PLANS.get(request.data.get("plan"))
        if plan is None:
            return Response({"plan": ["Choose Monthly or Annual."]},
                            status=status.HTTP_400_BAD_REQUEST)
        if not paymongo.configured():
            return Response({"detail": "Online payment is not set up yet."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        reference = services.new_reference(user)
        base = settings.FRONTEND_URL
        try:
            _session, url = paymongo.create_checkout(
                reader=user, plan=plan, reference=reference,
                success_url=f"{base}/subscribe/return?ref={reference}",
                cancel_url=f"{base}/subscribe?cancelled=1",
            )
        except paymongo.PayMongoError:
            log.exception("Checkout could not be opened for user %s", user.pk)
            return Response({"detail": "Payment could not be started. Try again in a moment."},
                            status=status.HTTP_502_BAD_GATEWAY)
        return Response({"checkout_url": url, "reference": reference})


class CheckoutStatusView(APIView):
    """Lets the return page say whether access was granted. It reads what
    the notification recorded; the visit itself grants nothing."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, reference):
        tx = (Transaction.objects.filter(reader=request.user, reference=reference)
              .select_related("subscription").first())
        if tx is None:
            return Response({"status": "pending"})
        if tx.status != Transaction.Status.SUCCEEDED:
            return Response({"status": "failed"})
        # Read afresh: the access was granted after this user was loaded.
        user = type(request.user).objects.select_related("reader_profile").get(pk=request.user.pk)
        return Response({"status": "paid", "plan": tx.plan,
                         "access_until": tx.subscription.current_period_end,
                         "entitled": is_entitled(user)})


@method_decorator(csrf_exempt, name="dispatch")
class PayMongoWebhookView(View):
    """PayMongo calls this after a payment. Nothing here trusts the request
    until its signature has been checked against the raw body."""

    def post(self, request):
        body = request.body
        if not paymongo.signature_ok(request.headers.get("Paymongo-Signature", ""), body):
            services.alert_admins(
                "signature", "A payment notification with a missing or wrong signature "
                             "was refused. If this repeats, check PAYMONGO_WEBHOOK_SECRET.")
            return JsonResponse({"detail": "Signature not recognised."}, status=400)
        try:
            event = json.loads(body)
            kind = event["data"]["attributes"]["type"]
        except (ValueError, KeyError, TypeError):
            return JsonResponse({"detail": "Not a PayMongo event."}, status=400)

        if kind != "checkout_session.payment.paid":
            return JsonResponse({"received": True, "outcome": "ignored"})
        try:
            outcome = services.record_checkout_payment(event)
        except (KeyError, TypeError):
            log.exception("Unexpected checkout notification shape")
            return JsonResponse({"detail": "Unexpected event shape."}, status=400)
        return JsonResponse({"received": True, "outcome": outcome})
