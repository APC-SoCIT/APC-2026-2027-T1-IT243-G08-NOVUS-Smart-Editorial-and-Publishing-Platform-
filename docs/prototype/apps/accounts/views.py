from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import (
    ChangePasswordSerializer, RegisterSerializer, UpdateProfileSerializer, UserSerializer,
)
from .throttles import PasswordChangeRateThrottle


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
