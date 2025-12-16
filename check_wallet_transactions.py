from wallet.models import WalletTransaction, Wallet

# Tìm ví "Vốn kinh doanh (VNĐ)"
try:
    wallet = Wallet.objects.get(name="Vốn kinh doanh (VNĐ)", currency="VND")
    print(f"Tìm thấy ví: {wallet.name}")
    print(f"Số dư: {wallet.balance}")
    print("\n" + "="*80)
    
    # Lấy 20 giao dịch gần nhất
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:20]
    print(f"20 giao dịch gần nhất:\n")
    
    for tx in transactions:
        print(f"ID: {tx.id}")
        print(f"  Type: {tx.transaction_type}")
        print(f"  Category: {tx.category}")
        print(f"  Amount: {tx.amount}")
        print(f"  Reference: '{tx.reference_code}'")
        print(f"  Description: {tx.description[:50]}...")
        print(f"  Date: {tx.transaction_date}")
        print("-" * 80)
        
except Wallet.DoesNotExist:
    print("Không tìm thấy ví 'Vốn kinh doanh (VNĐ)'")
