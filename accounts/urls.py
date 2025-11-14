from django.urls import path
from django.contrib.auth.views import LoginView
from .views import register_view

app_name = "accounts"

urlpatterns = [
    path("dang-nhap/", LoginView.as_view(template_name="accounts/login.html"), name="dang-nhap"),
    path("dang-ky/", register_view, name="dang-ky"),
]
