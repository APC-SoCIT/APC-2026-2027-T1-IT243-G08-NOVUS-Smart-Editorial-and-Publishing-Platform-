from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
 
from .sessions import SessionTokenRefreshSerializer
from .signin import SignInCodeView, SignInResendView, SignInView
 
from .throttles import RefreshRateThrottle, RegisterRateThrottle
from .views import (
    ChangePasswordView, ForgotPasswordView, MeView, RegisterView, ResetPasswordVerifyView,
    ResetPasswordView, WriterListView,
)
 
urlpatterns = [
    path("register/", RegisterView.as_view(throttle_classes=[RegisterRateThrottle]), name="register"),
    # UC-6.2 Authenticate User (Log In) — POST {email, password} -> {access, refresh}
    # Then, when a code is needed, the emailed code (signin.py).
    path("token/", SignInView.as_view(), name="token_obtain_pair"),
    path("token/code/", SignInCodeView.as_view(), name="token_code"),
    path("token/resend/", SignInResendView.as_view(), name="token_resend"),
    path("token/refresh/", TokenRefreshView.as_view(
        serializer_class=SessionTokenRefreshSerializer, throttle_classes=[RefreshRateThrottle]), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("password/", ChangePasswordView.as_view(), name="change_password"),
    # UC-5.2.2 Recover a Forgotten Password
    path("password/forgot/", ForgotPasswordView.as_view(), name="password_forgot"),
    path("password/reset/verify/", ResetPasswordVerifyView.as_view(), name="password_reset_verify"),
    path("password/reset/", ResetPasswordView.as_view(), name="password_reset"),
    path("writers/", WriterListView.as_view(), name="writers"),
]
