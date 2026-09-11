from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """UC-6.1 Register Account."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """UC-6.4 Update Profile Information. Login itself is handled by
    SimpleJWT's TokenObtainPairView (see accounts/urls.py) — UC-6.2."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


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
