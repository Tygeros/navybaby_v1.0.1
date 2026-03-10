from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class Wallet(models.Model):
    """
    Ví tiền tệ - Quản lý ví đa tiền tệ (VNĐ, CNY)
    """
    CURRENCY_CHOICES = [
        ('VND', 'Việt Nam Đồng (VNĐ)'),
        ('CNY', 'Đồng Nhân dân tệ (CNY)'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Tên ví")
    currency = models.CharField(
        max_length=10, 
        choices=CURRENCY_CHOICES,
        default="CNY", 
        verbose_name="Loại tiền tệ"
    )
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Số dư"
    )
    description = models.TextField(blank=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")

    class Meta:
        verbose_name = "Ví"
        verbose_name_plural = "Ví"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.currency})"

    def update_balance(self):
        """
        Tính toán lại số dư dựa trên các giao dịch
        """
        from django.db.models import Sum, Q
        
        # Tổng các khoản tăng (nạp tiền + khoản thu)
        deposits = self.transactions.filter(
            Q(transaction_type='deposit') | Q(transaction_type='income')
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Tổng các khoản giảm (rút tiền + khoản chi)
        withdrawals = self.transactions.filter(
            Q(transaction_type='withdrawal') | Q(transaction_type='expense')
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        self.balance = deposits - withdrawals
        self.save(update_fields=['balance', 'updated_at'])
        return self.balance


class WalletTransaction(models.Model):
    """
    Giao dịch ví - Lưu trữ các giao dịch nạp/rút tiền
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Nạp tiền'),
        ('withdrawal', 'Rút tiền / Chi tiêu'),
        ('income', 'Khoản thu'),
        ('expense', 'Khoản chi'),
    ]
    
    CATEGORY_CHOICES = [
        ('purchase', 'Mua hàng'),
        ('shipping', 'Phí vận chuyển'),
        ('deposit', 'Nạp tiền'),
        ('refund', 'Hoàn tiền'),
        ('other', 'Khác'),
    ]

    wallet = models.ForeignKey(
        Wallet, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        verbose_name="Ví"
    )
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES,
        verbose_name="Loại giao dịch"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name="Danh mục"
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Số tiền"
    )
    description = models.TextField(blank=True, verbose_name="Mô tả")
    reference_code = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Mã tham chiếu"
    )
    transaction_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Ngày giao dịch"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Giao dịch"
        verbose_name_plural = "Giao dịch"
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        type_display = dict(self.TRANSACTION_TYPES).get(self.transaction_type, '')
        return f"{type_display} - {self.amount} {self.wallet.currency} - {self.transaction_date.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        """
        Override save để tự động cập nhật số dư ví sau khi lưu giao dịch
        """
        super().save(*args, **kwargs)
        self.wallet.update_balance()

    def delete(self, *args, **kwargs):
        """
        Override delete để tự động cập nhật số dư ví sau khi xóa giao dịch
        """
        wallet = self.wallet
        super().delete(*args, **kwargs)
        wallet.update_balance()
