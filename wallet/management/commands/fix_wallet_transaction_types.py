from django.core.management.base import BaseCommand
from wallet.models import WalletTransaction
from finance.models import FinanceTransaction


class Command(BaseCommand):
    help = 'Cập nhật lại transaction_type cho các giao dịch ví được tạo tự động từ Finance Transaction'

    def handle(self, *args, **options):
        self.stdout.write("Bắt đầu cập nhật transaction_type cho giao dịch ví...")
        self.stdout.write("="*60)
        
        # Lấy tất cả giao dịch ví có reference_code bắt đầu bằng "TRANS-"
        wallet_transactions = WalletTransaction.objects.filter(
            reference_code__startswith="TRANS-"
        )
        
        updated_count = 0
        error_count = 0
        
        total = wallet_transactions.count()
        self.stdout.write(f"Tìm thấy {total} giao dịch ví cần kiểm tra...")
        
        for wallet_tx in wallet_transactions:
            try:
                # Lấy ID của finance transaction từ reference_code
                finance_id = wallet_tx.reference_code.replace("TRANS-", "")
                
                # Tìm finance transaction tương ứng
                finance_tx = FinanceTransaction.objects.get(id=finance_id)
                
                # Xác định transaction_type đúng
                if finance_tx.category:
                    if finance_tx.category.type == "INCOME":
                        correct_type = 'income'
                    else:  # EXPENSE
                        correct_type = 'expense'
                else:
                    # Nếu không có category, dựa vào số tiền
                    correct_type = 'income' if finance_tx.amount > 0 else 'expense'
                
                # Cập nhật nếu khác
                if wallet_tx.transaction_type != correct_type:
                    old_type = wallet_tx.transaction_type
                    wallet_tx.transaction_type = correct_type
                    wallet_tx.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Cập nhật {wallet_tx.reference_code}: {old_type} → {correct_type}"
                        )
                    )
                
            except FinanceTransaction.DoesNotExist:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Không tìm thấy Finance Transaction cho {wallet_tx.reference_code}"
                    )
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Lỗi khi xử lý {wallet_tx.reference_code}: {str(e)}"
                    )
                )
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("Hoàn thành!"))
        self.stdout.write(f"- Đã cập nhật: {updated_count} giao dịch")
        self.stdout.write(f"- Lỗi: {error_count} giao dịch")
        self.stdout.write(f"- Tổng cộng: {total} giao dịch")
        self.stdout.write("="*60)
