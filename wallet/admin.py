from django.contrib import admin
from .models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['name', 'currency', 'balance', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'currency', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'currency', 'description', 'is_active')
        }),
        ('Số dư', {
            'fields': ('balance',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_date', 'wallet', 'transaction_type', 'category', 'amount', 'reference_code']
    list_filter = ['transaction_type', 'category', 'transaction_date', 'wallet']
    search_fields = ['description', 'reference_code', 'wallet__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'transaction_date'
    fieldsets = (
        ('Thông tin giao dịch', {
            'fields': ('wallet', 'transaction_type', 'category', 'amount', 'transaction_date')
        }),
        ('Chi tiết', {
            'fields': ('description', 'reference_code')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
