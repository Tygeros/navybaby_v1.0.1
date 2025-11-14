from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from .views import register_view

app_name = "accounts"

urlpatterns = [
    path("dang-nhap/", LoginView.as_view(template_name="accounts/login.html"), name="dang-nhap"),
    path("dang-ky/", register_view, name="dang-ky"),
    path("dang-xuat/", LogoutView.as_view(next_page="accounts:dang-nhap"), name="dang-xuat"),
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
