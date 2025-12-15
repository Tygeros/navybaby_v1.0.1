from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Wallet, WalletTransaction
from decimal import Decimal


@login_required
def wallet_list(request):
    """
    Danh sách các ví
    """
    wallets = Wallet.objects.all()
    
    # Tính số dư theo từng loại tiền tệ
    vnd_balance = wallets.filter(currency='VND').aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    cny_balance = wallets.filter(currency='CNY').aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    
    context = {
        'wallets': wallets,
        'vnd_balance': vnd_balance,
        'cny_balance': cny_balance,
    }
    return render(request, 'wallet/wallet_list.html', context)


@login_required
def wallet_detail(request, wallet_id):
    """
    Chi tiết ví và danh sách giao dịch
    """
    wallet = get_object_or_404(Wallet, id=wallet_id)
    
    # Lọc giao dịch
    transactions = wallet.transactions.all()
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    transaction_type = request.GET.get('transaction_type')
    category = request.GET.get('category')
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            transactions = transactions.filter(transaction_date__gte=start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            transactions = transactions.filter(transaction_date__lte=end_dt)
        except ValueError:
            pass
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if category:
        transactions = transactions.filter(category=category)
    
    # Thống kê
    total_deposits = wallet.transactions.filter(
        transaction_type='deposit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_withdrawals = wallet.transactions.filter(
        transaction_type='withdrawal'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'start_date': start_date,
        'end_date': end_date,
        'transaction_type': transaction_type,
        'category': category,
        'transaction_types': WalletTransaction.TRANSACTION_TYPES,
        'categories': WalletTransaction.CATEGORY_CHOICES,
    }
    return render(request, 'wallet/wallet_detail.html', context)


@login_required
def wallet_create(request):
    """
    Tạo ví mới
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        currency = request.POST.get('currency', 'CNY')
        description = request.POST.get('description', '')
        initial_balance = request.POST.get('initial_balance', '0')
        
        if name:
            try:
                balance_decimal = Decimal(initial_balance) if initial_balance else Decimal('0.00')
                if balance_decimal < 0:
                    raise ValueError('Số dư ban đầu không được âm')
                
                wallet = Wallet.objects.create(
                    name=name,
                    currency=currency,
                    description=description,
                    balance=balance_decimal
                )
                messages.success(request, f'Đã tạo ví "{wallet.name}" thành công với số dư ban đầu {balance_decimal} {currency}!')
                return redirect('wallet:wallet_detail', wallet_id=wallet.id)
            except (ValueError, TypeError) as e:
                messages.error(request, f'Lỗi: {str(e)}')
        else:
            messages.error(request, 'Vui lòng nhập tên ví!')
    
    return render(request, 'wallet/wallet_form.html')


@login_required
def wallet_edit(request, wallet_id):
    """
    Chỉnh sửa thông tin ví và điều chỉnh số dư thủ công
    """
    wallet = get_object_or_404(Wallet, id=wallet_id)
    
    if request.method == 'POST':
        wallet.name = request.POST.get('name', wallet.name)
        wallet.currency = request.POST.get('currency', wallet.currency)
        wallet.description = request.POST.get('description', '')
        wallet.is_active = request.POST.get('is_active') == 'on'
        
        # Xử lý điều chỉnh số dư thủ công
        balance_adjustment = request.POST.get('balance_adjustment', '')
        adjustment_note = request.POST.get('adjustment_note', '')
        
        if balance_adjustment:
            try:
                adjustment_amount = Decimal(balance_adjustment)
                if adjustment_amount != 0:
                    # Tạo giao dịch ghi nhật ký
                    transaction_type = 'deposit' if adjustment_amount > 0 else 'withdrawal'
                    abs_amount = abs(adjustment_amount)
                    
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type=transaction_type,
                        category='other',
                        amount=abs_amount,
                        description=f'Điều chỉnh số dư thủ công: {adjustment_note}' if adjustment_note else 'Điều chỉnh số dư thủ công',
                        reference_code='MANUAL_ADJUSTMENT',
                        transaction_date=timezone.now()
                    )
                    messages.success(request, f'Đã điều chỉnh số dư {adjustment_amount:+.2f} {wallet.currency}')
            except (ValueError, TypeError) as e:
                messages.error(request, f'Lỗi điều chỉnh số dư: {str(e)}')
        
        wallet.save()
        messages.success(request, f'Đã cập nhật ví "{wallet.name}" thành công!')
        return redirect('wallet:wallet_detail', wallet_id=wallet.id)
    
    context = {'wallet': wallet}
    return render(request, 'wallet/wallet_form.html', context)


@login_required
def wallet_delete(request, wallet_id):
    """
    Xóa ví
    """
    wallet = get_object_or_404(Wallet, id=wallet_id)
    transaction_count = wallet.transactions.count()
    
    if request.method == 'POST':
        wallet_name = wallet.name
        wallet.delete()
        messages.success(request, f'Đã xóa ví "{wallet_name}" và {transaction_count} giao dịch liên quan!')
        return redirect('wallet:wallet_list')
    
    context = {
        'wallet': wallet,
        'transaction_count': transaction_count,
    }
    return render(request, 'wallet/wallet_confirm_delete.html', context)


@login_required
def transaction_create(request, wallet_id):
    """
    Tạo giao dịch mới
    """
    wallet = get_object_or_404(Wallet, id=wallet_id)
    
    if request.method == 'POST':
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')
        reference_code = request.POST.get('reference_code', '')
        transaction_date = request.POST.get('transaction_date')
        
        try:
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                raise ValueError('Số tiền phải lớn hơn 0')
            
            # Parse transaction date
            if transaction_date:
                trans_dt = datetime.strptime(transaction_date, '%Y-%m-%dT%H:%M')
                trans_dt = timezone.make_aware(trans_dt)
            else:
                trans_dt = timezone.now()
            
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=transaction_type,
                category=category,
                amount=amount_decimal,
                description=description,
                reference_code=reference_code,
                transaction_date=trans_dt
            )
            
            messages.success(request, 'Đã thêm giao dịch thành công!')
            return redirect('wallet:wallet_detail', wallet_id=wallet.id)
        except (ValueError, TypeError) as e:
            messages.error(request, f'Lỗi: {str(e)}')
    
    context = {
        'wallet': wallet,
        'transaction_types': WalletTransaction.TRANSACTION_TYPES,
        'categories': WalletTransaction.CATEGORY_CHOICES,
    }
    return render(request, 'wallet/transaction_form.html', context)


@login_required
def transaction_edit(request, transaction_id):
    """
    Chỉnh sửa giao dịch
    """
    transaction = get_object_or_404(WalletTransaction, id=transaction_id)
    wallet = transaction.wallet
    
    if request.method == 'POST':
        transaction.transaction_type = request.POST.get('transaction_type', transaction.transaction_type)
        transaction.category = request.POST.get('category', transaction.category)
        transaction.description = request.POST.get('description', '')
        transaction.reference_code = request.POST.get('reference_code', '')
        
        amount = request.POST.get('amount')
        transaction_date = request.POST.get('transaction_date')
        
        try:
            if amount:
                amount_decimal = Decimal(amount)
                if amount_decimal <= 0:
                    raise ValueError('Số tiền phải lớn hơn 0')
                transaction.amount = amount_decimal
            
            if transaction_date:
                trans_dt = datetime.strptime(transaction_date, '%Y-%m-%dT%H:%M')
                transaction.transaction_date = timezone.make_aware(trans_dt)
            
            transaction.save()
            messages.success(request, 'Đã cập nhật giao dịch thành công!')
            return redirect('wallet:wallet_detail', wallet_id=wallet.id)
        except (ValueError, TypeError) as e:
            messages.error(request, f'Lỗi: {str(e)}')
    
    context = {
        'wallet': wallet,
        'transaction': transaction,
        'transaction_types': WalletTransaction.TRANSACTION_TYPES,
        'categories': WalletTransaction.CATEGORY_CHOICES,
    }
    return render(request, 'wallet/transaction_form.html', context)


@login_required
def transaction_delete(request, transaction_id):
    """
    Xóa giao dịch
    """
    transaction = get_object_or_404(WalletTransaction, id=transaction_id)
    wallet = transaction.wallet
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Đã xóa giao dịch thành công!')
        return redirect('wallet:wallet_detail', wallet_id=wallet.id)
    
    context = {
        'transaction': transaction,
        'wallet': wallet,
    }
    return render(request, 'wallet/transaction_confirm_delete.html', context)
