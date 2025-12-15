from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal


@receiver(post_save, sender='finance.FinanceTransaction')
def sync_wallet_transaction_from_finance(sender, instance, created, **kwargs):
    """
    Tự động tạo/cập nhật giao dịch ví khi có giao dịch tài chính mới hoặc chỉnh sửa
    """
    # Import ở đây để tránh circular import
    from wallet.models import Wallet, WalletTransaction
    
    # Tìm ví "Vốn kinh doanh (VNĐ)"
    try:
        wallet = Wallet.objects.get(name="Vốn kinh doanh (VNĐ)", currency="VND")
    except Wallet.DoesNotExist:
        # Nếu không tìm thấy ví, không tạo giao dịch
        return
    
    # Xác định loại giao dịch dựa trên category type
    if instance.category:
        if instance.category.type == "INCOME":
            transaction_type = 'income'  # Khoản thu
        else:  # EXPENSE
            transaction_type = 'expense'  # Khoản chi
    else:
        # Nếu không có category, dựa vào số tiền
        transaction_type = 'income' if instance.amount > 0 else 'expense'
    
    # Mã tham chiếu theo format TRANS-{id}
    reference_code = f"TRANS-{instance.id}"
    
    # Lấy tên danh mục cho mô tả
    category_name = instance.category.name if instance.category else "Không có danh mục"
    description = f"Giao dịch tài chính: {category_name}"
    if instance.note:
        description += f" - {instance.note}"
    
    if created:
        # Tạo giao dịch ví mới
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            category='other',
            amount=abs(instance.amount),
            description=description,
            reference_code=reference_code,
            transaction_date=timezone.now()
        )
    else:
        # Cập nhật giao dịch ví hiện có
        try:
            wallet_transaction = WalletTransaction.objects.get(
                reference_code=reference_code,
                wallet=wallet
            )
            wallet_transaction.transaction_type = transaction_type
            wallet_transaction.amount = abs(instance.amount)
            wallet_transaction.description = description
            wallet_transaction.save()
        except WalletTransaction.DoesNotExist:
            # Nếu không tìm thấy, tạo mới
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=transaction_type,
                category='other',
                amount=abs(instance.amount),
                description=description,
                reference_code=reference_code,
                transaction_date=timezone.now()
            )


@receiver(post_delete, sender='finance.FinanceTransaction')
def delete_wallet_transaction_from_finance(sender, instance, **kwargs):
    """
    Tự động xóa giao dịch ví khi xóa giao dịch tài chính
    """
    from wallet.models import Wallet, WalletTransaction
    
    # Tìm ví "Vốn kinh doanh (VNĐ)"
    try:
        wallet = Wallet.objects.get(name="Vốn kinh doanh (VNĐ)", currency="VND")
    except Wallet.DoesNotExist:
        return
    
    # Mã tham chiếu theo format TRANS-{id}
    reference_code = f"TRANS-{instance.id}"
    
    # Xóa giao dịch ví tương ứng
    WalletTransaction.objects.filter(
        reference_code=reference_code,
        wallet=wallet
    ).delete()
