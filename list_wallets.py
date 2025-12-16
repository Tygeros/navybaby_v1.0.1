from wallet.models import Wallet, WalletTransaction

print("Danh sách tất cả các ví:")
print("="*80)
wallets = Wallet.objects.all()
for wallet in wallets:
    print(f"ID: {wallet.id}")
    print(f"  Tên: '{wallet.name}'")
    print(f"  Currency: {wallet.currency}")
    print(f"  Số dư: {wallet.balance}")
    tx_count = WalletTransaction.objects.filter(wallet=wallet).count()
    print(f"  Số giao dịch: {tx_count}")
    print("-" * 80)

print("\nKiểm tra giao dịch có mô tả chứa 'Giao dịch tài chính':")
print("="*80)
finance_txs = WalletTransaction.objects.filter(description__contains="Giao dịch tài chính")[:10]
print(f"Tìm thấy {finance_txs.count()} giao dịch")
for tx in finance_txs:
    print(f"\nID: {tx.id}")
    print(f"  Ví: {tx.wallet.name}")
    print(f"  Type: {tx.transaction_type}")
    print(f"  Amount: {tx.amount}")
    print(f"  Reference: '{tx.reference_code}'")
    print(f"  Description: {tx.description[:80]}")
