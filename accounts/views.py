from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(request, username=username, password=raw_password)
            if user is not None:
                login(request, user)
                messages.success(request, "Đăng ký thành công. Bạn đã được đăng nhập.")
                return redirect("home")
            messages.success(request, "Đăng ký thành công. Vui lòng đăng nhập.")
            return redirect("accounts:dang-nhap")
    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})
