from django.http import JsonResponse


class MaintenanceModeMiddleware:
    """
    UC-4.3 Toggle Maintenance Mode.

    Blocks public reads while leaving authentication, the admin, and the
    settings endpoint reachable — otherwise an Admin could switch maintenance
    on and lock themselves out of switching it off.
    """

    EXEMPT_PREFIXES = ("/admin", "/api/auth", "/api/platform", "/media", "/static")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        from .models import PlatformSetting
        try:
            setting = PlatformSetting.load()
        except Exception:
            # Before the first migration the table may not exist yet.
            return self.get_response(request)

        if not setting.maintenance_mode:
            return self.get_response(request)

        # Staff keep working during maintenance; only public traffic is held.
        user = getattr(request, "user", None)
        if user and user.is_authenticated and user.role != user.Role.READER:
            return self.get_response(request)

        return JsonResponse(
            {"maintenance": True, "detail": setting.maintenance_message},
            status=503,
        )
