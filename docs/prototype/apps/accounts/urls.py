from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .throttles import LoginRateThrottle, RefreshRateThrottle, RegisterRateThrottle
from .views import (
    ChangePasswordView, ForgotPasswordView, MeView, RegisterView, ResetPasswordVerifyView,
    ResetPasswordView, WriterListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(throttle_classes=[RegisterRateThrottle]), name="register"),
    # UC-6.2 Authenticate User (Log In) — POST {email, password} -> {access, refresh}
    path("token/", TokenObtainPairView.as_view(throttle_classes=[LoginRateThrottle]), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(throttle_classes=[RefreshRateThrottle]), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("password/", ChangePasswordView.as_view(), name="change_password"),
    # UC-5.2.2 Recover a Forgotten Password
    path("password/forgot/", ForgotPasswordView.as_view(), name="password_forgot"),
    path("password/reset/verify/", ResetPasswordVerifyView.as_view(), name="password_reset_verify"),
    path("password/reset/", ResetPasswordView.as_view(), name="password_reset"),
    path("writers/", WriterListView.as_view(), name="writers"),
]
