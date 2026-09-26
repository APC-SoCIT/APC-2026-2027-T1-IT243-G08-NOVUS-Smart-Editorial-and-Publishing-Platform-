from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .throttles import LoginRateThrottle, RefreshRateThrottle, RegisterRateThrottle
from .views import MeView, RegisterView, WriterListView

urlpatterns = [
    path("register/", RegisterView.as_view(throttle_classes=[RegisterRateThrottle]), name="register"),
    # UC-6.2 Authenticate User (Log In) — POST {email, password} -> {access, refresh}
    path("token/", TokenObtainPairView.as_view(throttle_classes=[LoginRateThrottle]), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(throttle_classes=[RefreshRateThrottle]), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("writers/", WriterListView.as_view(), name="writers"),
]
