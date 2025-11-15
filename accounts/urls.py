from django.urls import path
from django.contrib.auth.views import LogoutView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from .views import register_view, CustomLoginView, pending_approval_view

app_name = "accounts"

urlpatterns = [
    path("dang-nhap/", CustomLoginView.as_view(template_name="accounts/login.html"), name="dang-nhap"),
    path("dang-ky/", register_view, name="dang-ky"),
    path("dang-xuat/", LogoutView.as_view(next_page="accounts:dang-nhap"), name="dang-xuat"),
    path("cho-duyet/", pending_approval_view, name="cho-duyet"),
    path(
        "cai-dat/mat-khau/",
        login_required(
            PasswordChangeView.as_view(
                template_name="accounts/password_change.html",
                success_url=reverse_lazy("home"),
            )
        ),
        name="doi-mat-khau",
    ),
]
