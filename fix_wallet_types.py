from wallet.models import WalletTransaction
from finance.models import FinanceTransaction

# Lấy tất cả giao dịch ví có reference_code bắt đầu bằng "TRANS-"
wallet_transactions = WalletTransaction.objects.filter(reference_code__startswith="TRANS-")

updated_count = 0
error_count = 0

print(f"Tìm thấy {wallet_transactions.count()} giao dịch ví cần kiểm tra...")

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
            print(f"✓ Cập nhật {wallet_tx.reference_code}: {old_type} → {correct_type}")
        
    except FinanceTransaction.DoesNotExist:
        error_count += 1
        print(f"✗ Không tìm thấy Finance Transaction cho {wallet_tx.reference_code}")
    except Exception as e:
        error_count += 1
        print(f"✗ Lỗi khi xử lý {wallet_tx.reference_code}: {str(e)}")

print("\n" + "="*60)
print(f"Hoàn thành!")
print(f"- Đã cập nhật: {updated_count} giao dịch")
print(f"- Lỗi: {error_count} giao dịch")
print(f"- Tổng cộng: {wallet_transactions.count()} giao dịch")
print("="*60)
