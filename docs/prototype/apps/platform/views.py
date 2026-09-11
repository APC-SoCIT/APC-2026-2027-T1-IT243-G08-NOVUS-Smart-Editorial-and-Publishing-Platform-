from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import PlatformSetting
from .serializers import PlatformSettingSerializer


class IsAdmin(permissions.BasePermission):
    message = "Administrator access is required."

    def has_permission(self, request, view):
        u = request.user
        if request.method in permissions.SAFE_METHODS:
            return True  # the public site needs to know if maintenance is on
        return bool(u and u.is_authenticated
                    and (u.role == User.Role.ADMIN or u.is_superuser))


class PlatformSettingView(APIView):
    """Module 4: read by anyone, changed only by an Admin."""

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(PlatformSettingSerializer(PlatformSetting.load()).data)

    def patch(self, request):
        setting = PlatformSetting.load()
        serializer = PlatformSettingSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)
