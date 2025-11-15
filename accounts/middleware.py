from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.conf import settings


class ApprovalRequiredMiddleware:
    """
    Redirect authenticated but unapproved users to the pending approval page.

    Allows access to:
    - Auth pages: login, logout, register
    - Pending approval page
    - Admin (for superusers) and superusers bypass in general
    - Static/media
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow static and media
        path = request.path
        if path.startswith(settings.STATIC_URL or "/static/"):
            return self.get_response(request)
        if getattr(settings, "MEDIA_URL", None) and path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        # Skip for anonymous users
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        # Superusers bypass
        if getattr(user, "is_superuser", False):
            return self.get_response(request)

        # Resolve current url name (may be None)
        try:
            resolver_match = resolve(path)
            url_name = resolver_match.url_name
            app_name = resolver_match.app_name
        except Exception:
            url_name = None
            app_name = None

        # Allowed names for unapproved users
        allowed_names = {
            ("accounts", "dang-nhap"),
            ("accounts", "dang-xuat"),
            ("accounts", "dang-ky"),
            ("accounts", "cho-duyet"),
        }

        if (app_name, url_name) in allowed_names:
            return self.get_response(request)

        # If not approved, redirect to pending
        if not getattr(user, "is_approved", False):
            return redirect("accounts:cho-duyet")

        return self.get_response(request)
