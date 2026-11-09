from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.db import transaction
from rest_framework import status

from apps.notifications.email import send_email

from .models import PasswordResetToken, User
from .serializers import (
    INVALID_LINK, ChangePasswordSerializer, ForgotPasswordSerializer, RegisterSerializer,
    ResetPasswordSerializer, UpdateProfileSerializer, UserSerializer,
)
from .throttles import (
    PasswordChangeRateThrottle, PasswordResetConfirmThrottle, PasswordResetRequestThrottle,
)


class RegisterView(generics.CreateAPIView):
    """UC-6.1 Register Account."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """UC-6.4 Update Profile Information. Login itself is handled by
    SimpleJWT's TokenObtainPairView (see accounts/urls.py) — UC-6.2."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        # Reads return the full profile including role and subscription tier;
        # writes accept only what the owner may change. Using one serializer
        # for both would have let a PATCH set its own role.
        if self.request.method in ("PATCH", "PUT"):
            return UpdateProfileSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Return the full profile so the client refreshes its own state
        # rather than holding the trimmed write shape.
        return Response(UserSerializer(self.get_object()).data)


class WriterListView(APIView):
    """Writers available for assignment (UC-1.1). Editors only — this is a
    staff directory, not public data."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in (User.Role.EDITOR, User.Role.ADMIN):
            return Response([], status=403)
        writers = User.objects.filter(role=User.Role.WRITER, is_active=True)
        return Response([
            {"id": w.id, "first_name": w.first_name, "last_name": w.last_name}
            for w in writers
        ])


class ChangePasswordView(APIView):
    """Change one's own password, by choice or because it has expired.
    Clears must_reset_password, which unlocks an expired account."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PasswordChangeRateThrottle]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_reset_password = False
        user.save()
        return Response(UserSerializer(user).data)


RESET_SENT = "If an account uses that address, we've sent a reset link."


class ForgotPasswordView(APIView):
    """UC-5.2.2 steps 1-2: ask for a reset link.

    The answer is the same whether or not the address has an account, so the
    page cannot be used to find out who is registered (NFR-12). Suspended and
    deactivated accounts get no email: a new password would not let them in.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True, is_suspended=False).first()
        if user is not None:
            raw = PasswordResetToken.issue(user, ip=request.META.get("REMOTE_ADDR", ""))
            minutes = getattr(settings, "PASSWORD_RESET_MINUTES", 60)
            send_email(user, "password_reset", "Reset your password", {
                "reset_url": f"{settings.FRONTEND_URL}/reset-password?token={raw}",
                "minutes": minutes,
            })
        return Response({"detail": RESET_SENT})


class ResetPasswordVerifyView(APIView):
    """UC-5.2.2 step 4: check a link before showing the new-password form."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        token = PasswordResetToken.find_valid(str(request.data.get("token", "")))
        if token is None:
            return Response(INVALID_LINK, status=status.HTTP_400_BAD_REQUEST)
        return Response({"valid": True})


class ResetPasswordView(APIView):
    """UC-5.2.2 step 5: set the new password and spend the link."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        token = PasswordResetToken.find_valid(str(request.data.get("token", "")))
        if token is None:
            return Response(INVALID_LINK, status=status.HTTP_400_BAD_REQUEST)
        user = token.user
        serializer = ResetPasswordSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            # Lock the row so two submissions of one link cannot both succeed.
            locked = (PasswordResetToken.objects.select_for_update()
                      .filter(pk=token.pk, used_at__isnull=True).first())
            if locked is None:
                return Response(INVALID_LINK, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data["new_password"])
            user.must_reset_password = False
            user.save()
            locked.redeem()
        return Response({
            "detail": "Password updated. Sign in with your new password.",
            "staff": user.role != User.Role.READER,
        })
