from django.urls import path

from .views import (
    CancelSubscriptionView, CheckoutStatusView, CheckoutView, PayMongoWebhookView,
    PlanListView, SubscriptionView,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="payment_plans"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("checkout/<str:reference>/", CheckoutStatusView.as_view(), name="checkout_status"),
    path("webhook/", PayMongoWebhookView.as_view(), name="paymongo_webhook"),
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("subscription/cancel/", CancelSubscriptionView.as_view(), name="subscription_cancel"),
]
