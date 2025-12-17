from django.core.management.base import BaseCommand
from django.utils import timezone
from wallet.models import Wallet, WalletTransaction
from finance.models import FinanceTransaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Tự động clone các giao dịch từ Finance vào Ví kinh doanh (VNĐ)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Đồng bộ tất cả giao dịch Finance (bao gồm cả những giao dịch đã đồng bộ)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ hiển thị những gì sẽ được đồng bộ mà không thực sự tạo giao dịch',
        )

    def handle(self, *args, **options):
        self.stdout.write("="*60)
        self.stdout.write(self.style.SUCCESS("Bắt đầu đồng bộ giao dịch Finance → Ví"))
        self.stdout.write("="*60)
        
        # Tìm hoặc tạo ví "Vốn kinh doanh (VNĐ)"
        wallet, created = Wallet.objects.get_or_create(
            name="Vốn kinh doanh (VNĐ)",
            currency="VND",
            defaults={
                'description': 'Ví tự động đồng bộ từ giao dịch tài chính',
                'balance': Decimal('0.00')
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Đã tạo ví mới: {wallet.name}'))
        else:
            self.stdout.write(f'Sử dụng ví hiện có: {wallet.name}')
        
        # Lấy tất cả giao dịch Finance
        finance_transactions = FinanceTransaction.objects.all().order_by('created_at')
        total_finance = finance_transactions.count()
        
        self.stdout.write(f'\nTìm thấy {total_finance} giao dịch Finance')
        
        # Lấy danh sách các giao dịch đã đồng bộ
        if options['all']:
            self.stdout.write(self.style.WARNING('Chế độ --all: Sẽ đồng bộ lại tất cả giao dịch'))
            synced_refs = set()
        else:
            synced_refs = set(
                WalletTransaction.objects.filter(
                    wallet=wallet,
                    reference_code__startswith='TRANS-'
                ).values_list('reference_code', flat=True)
            )
            self.stdout.write(f'Đã có {len(synced_refs)} giao dịch được đồng bộ trước đó')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for finance_tx in finance_transactions:
            reference_code = f"TRANS-{finance_tx.id}"
            
            # Kiểm tra xem đã đồng bộ chưa
            if not options['all'] and reference_code in synced_refs:
                skipped_count += 1
                continue
            
            try:
                # Xác định loại giao dịch
                if finance_tx.category:
                    if finance_tx.category.type == "INCOME":
                        transaction_type = 'income'
                        type_label = "Khoản thu"
                    else:  # EXPENSE
                        transaction_type = 'expense'
                        type_label = "Khoản chi"
                else:
                    transaction_type = 'income' if finance_tx.amount > 0 else 'expense'
                    type_label = "Khoản thu" if finance_tx.amount > 0 else "Khoản chi"
                
                # Tạo mô tả
                category_name = finance_tx.category.name if finance_tx.category else "Không có danh mục"
                description = f"Giao dịch tài chính: {category_name}"
                if finance_tx.note:
                    description += f" - {finance_tx.note}"
                
                # Kiểm tra dry-run
                if options['dry_run']:
                    self.stdout.write(
                        f"[DRY-RUN] Sẽ tạo: {reference_code} | {type_label} | "
                        f"{abs(finance_tx.amount):,.0f}đ | {category_name}"
                    )
                    created_count += 1
                    continue
                
                # Tạo hoặc cập nhật giao dịch ví
                wallet_tx, tx_created = WalletTransaction.objects.update_or_create(
                    wallet=wallet,
                    reference_code=reference_code,
                    defaults={
                        'transaction_type': transaction_type,
                        'category': 'other',
                        'amount': abs(finance_tx.amount),
                        'description': description,
                        'transaction_date': finance_tx.created_at,
                    }
                )
                
                if tx_created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Tạo mới: {reference_code} | {type_label} | "
                            f"{abs(finance_tx.amount):,.0f}đ"
                        )
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"↻ Cập nhật: {reference_code} | {type_label} | "
                            f"{abs(finance_tx.amount):,.0f}đ"
                        )
                    )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Lỗi với Finance Transaction ID={finance_tx.id}: {str(e)}"
                    )
                )
        
        # Cập nhật số dư ví
        if not options['dry_run']:
            old_balance = wallet.balance
            wallet.update_balance()
            self.stdout.write(
                f"\n💰 Số dư ví: {old_balance:,.0f}đ → {wallet.balance:,.0f}đ"
            )
        
        # Tổng kết
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("Hoàn thành!"))
        self.stdout.write("="*60)
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("Chế độ DRY-RUN: Không có thay đổi thực tế"))
        
        self.stdout.write(f"📊 Tổng giao dịch Finance: {total_finance}")
        self.stdout.write(f"✓ Đã tạo mới: {created_count}")
        self.stdout.write(f"↻ Đã cập nhật: {updated_count}")
        self.stdout.write(f"⊘ Đã bỏ qua: {skipped_count}")
        self.stdout.write(f"✗ Lỗi: {error_count}")
        self.stdout.write("="*60)
