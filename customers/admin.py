from django.contrib import admin
from .models import Customer, QRCode


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "phone_number", "is_affiliate", "created_at")
    search_fields = ("code", "name", "phone_number")
    list_filter = ("is_affiliate",)


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "file", "created_at")
    search_fields = ("name", "file")
