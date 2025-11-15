from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(request, username=username, password=raw_password)
            if user is not None:
                login(request, user)
                messages.success(request, "Đăng ký thành công. Tài khoản đang chờ được chấp thuận.")
                return redirect("accounts:cho-duyet")
            messages.success(request, "Đăng ký thành công. Vui lòng đăng nhập.")
            return redirect("accounts:dang-nhap")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


class CustomLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user
        if getattr(user, "is_authenticated", False) and not getattr(user, "is_approved", True):
            return reverse_lazy("accounts:cho-duyet")
        return super().get_success_url()


@login_required
def pending_approval_view(request):
    # Nếu đã được duyệt rồi thì đưa về trang chủ
    if getattr(request.user, "is_approved", False):
        return redirect("home")
    return render(request, "accounts/pending_approval.html")
