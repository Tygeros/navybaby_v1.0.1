from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from django.db.models import Sum, Case, When, DecimalField, F, Count, Value
from django.db.models.functions import Coalesce
from decimal import Decimal

from .models import FinanceCategory, FinanceTransaction
from orders.models import Order
from customers.models import Customer
from .forms import FinanceCategoryForm, FinanceTransactionForm


class CategoryListView(ListView):
    model = FinanceCategory
    template_name = 'finance/categories_list.html'
    context_object_name = 'categories'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        t = self.request.GET.get('type', '')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if t in dict(FinanceCategory.TYPE_CHOICES):
            qs = qs.filter(type=t)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Danh mục tài chính - NavyBaby'
        ctx['type'] = self.request.GET.get('type', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class CategoryCreateView(CreateView):
    model = FinanceCategory
    form_class = FinanceCategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('finance:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Đã tạo danh mục tài chính!')
        return super().form_valid(form)


class IncomeQuickConfirmView(View):
    def get(self, request, *args, **kwargs):
        # Read params
        cust_param = (request.GET.get('customer') or '').strip()
        amt_param = (request.GET.get('amount') or '').strip()
        note = request.GET.get('note') or ''
        # Resolve customer by id or code
        customer = None
        if cust_param:
            if cust_param.isdigit():
                customer = Customer.objects.filter(id=int(cust_param)).first()
            if customer is None:
                customer = Customer.objects.filter(code=cust_param).first()
        # Parse amount
        amount = None
        try:
            amount = Decimal(str(float(amt_param))) if amt_param else None
        except Exception:
            amount = None
        if not customer or amount is None or amount <= 0:
            messages.error(request, 'Thiếu thông tin hợp lệ để tạo giao dịch thanh toán.')
            return redirect('finance:transactions_list')
        # Find or create category
        cat_name = 'KH thanh toán đơn hàng'
        category = FinanceCategory.objects.filter(type='INCOME', name__iexact=cat_name).first()
        if category is None:
            category = FinanceCategory.objects.create(type='INCOME', name=cat_name, description='Tự động tạo')
        # Create transaction
        FinanceTransaction.objects.create(
            category=category,
            amount=amount,
            customer=customer,
            note=(note or customer.code or ''),
        )
        # If a deposit was deducted on the bill, auto-create a deduction expense transaction
        paid_override = (request.GET.get('paid_override') or '').strip()
        try:
            paid_override_dec = Decimal(str(float(paid_override))) if paid_override else Decimal('0')
        except Exception:
            paid_override_dec = Decimal('0')
        if paid_override_dec > 0:
            expense_name = 'Khấu trừ khoản tiền đặt cọc'
            expense_cat = FinanceCategory.objects.filter(type='EXPENSE', name__iexact=expense_name).first()
            if expense_cat is None:
                expense_cat = FinanceCategory.objects.create(type='EXPENSE', name=expense_name, description='Tự động tạo')
            FinanceTransaction.objects.create(
                category=expense_cat,
                amount=paid_override_dec,
                customer=customer,
                note=(note or customer.code or ''),
            )
        # Also move all orders in the current bill (same filters) to 'reconciled'
        qs = Order.objects.filter(customer=customer).select_related('product')
        status_list = request.GET.getlist('status')
        if status_list:
            qs = qs.filter(status__in=status_list)
        supplier_ids = request.GET.getlist('supplier')
        if supplier_ids:
            qs = qs.filter(product__supplier_id__in=supplier_ids)
        q = request.GET.get('q')
        if q:
            from django.db import models as dj_models
            qs = qs.filter(dj_models.Q(code__icontains=q) | dj_models.Q(product__name__icontains=q))
        qs.update(status='reconciled')
        messages.success(request, 'Đã xác nhận thanh toán và tạo giao dịch!')
        return redirect('finance:transactions_list')

class CategoryUpdateView(UpdateView):
    model = FinanceCategory
    form_class = FinanceCategoryForm
    template_name = 'finance/category_form.html'

    def get_success_url(self):
        return reverse_lazy('finance:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Đã cập nhật danh mục!')
        return super().form_valid(form)


class CategoryDeleteView(DeleteView):
    model = FinanceCategory
    template_name = 'finance/category_confirm_delete.html'
    success_url = reverse_lazy('finance:category_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Đã xóa danh mục!')
        return super().delete(request, *args, **kwargs)


class TransactionListView(ListView):
    model = FinanceTransaction
    template_name = 'finance/transactions_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'customer')
        q = (self.request.GET.get('q', '') or '').strip()
        t = self.request.GET.get('type', '')
        # Support multi-select categories like orders status filter
        raw_cats = self.request.GET.getlist('category')
        valid_category_ids = set(FinanceCategory.objects.values_list('id', flat=True))
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if q:
            qs = qs.filter(
                Q(customer__name__icontains=q)
                | Q(customer__phone_number__icontains=q)
                | Q(customer__code__icontains=q)
            )
        if t in dict(FinanceCategory.TYPE_CHOICES):
            qs = qs.filter(category__type=t)
        # Filter by multiple categories if provided
        selected_cat_ids = [int(c) for c in raw_cats if c.isdigit() and int(c) in valid_category_ids]
        if selected_cat_ids:
            qs = qs.filter(category_id__in=selected_cat_ids)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        sort = self.request.GET.get('sort', 'created_desc')
        if sort == 'created_asc':
            qs = qs.order_by('created_at')
        elif sort == 'amount_desc':
            qs = qs.order_by('-amount', '-created_at')
        elif sort == 'amount_asc':
            qs = qs.order_by('amount', '-created_at')
        else:  # created_desc (default)
            qs = qs.order_by('-created_at')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nhật ký giao dịch - NavyBaby'
        categories_qs = FinanceCategory.objects.all().order_by('name')
        ctx['categories'] = categories_qs
        ctx['q'] = self.request.GET.get('q', '')
        ctx['type'] = self.request.GET.get('type', '')
        raw_cats = self.request.GET.getlist('category')
        valid_ids = set(categories_qs.values_list('id', flat=True))
        ctx['category_filter'] = [c for c in raw_cats if c.isdigit() and int(c) in valid_ids]
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        ctx['sort'] = self.request.GET.get('sort', 'created_desc')

        # Aggregated stats over the same filtered set (not paginated)
        filtered = FinanceTransaction.objects.select_related('category', 'customer')
        t = self.request.GET.get('type', '')
        raw_cats = self.request.GET.getlist('category')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        q = (self.request.GET.get('q', '') or '').strip()
        if q:
            filtered = filtered.filter(
                Q(customer__name__icontains=q)
                | Q(customer__phone_number__icontains=q)
                | Q(customer__code__icontains=q)
            )
        if t in dict(FinanceCategory.TYPE_CHOICES):
            filtered = filtered.filter(category__type=t)
        selected_cat_ids = [int(c) for c in raw_cats if c.isdigit() and int(c) in valid_ids]
        if selected_cat_ids:
            filtered = filtered.filter(category_id__in=selected_cat_ids)
        if date_from:
            filtered = filtered.filter(created_at__date__gte=date_from)
        if date_to:
            filtered = filtered.filter(created_at__date__lte=date_to)
        
        dec_field = DecimalField(max_digits=15, decimal_places=2)
        zero_dec = Value(0, output_field=dec_field)
        sums = filtered.aggregate(
            total_count=Count('id'),
            inflow=Coalesce(
                Sum(
                    Case(
                        When(category__type='INCOME', then=F('amount')),
                        default=zero_dec,
                        output_field=dec_field,
                    )
                ),
                zero_dec,
            ),
            outflow=Coalesce(
                Sum(
                    Case(
                        When(category__type='EXPENSE', then=F('amount')),
                        default=zero_dec,
                        output_field=dec_field,
                    )
                ),
                zero_dec,
            ),
        )
        try:
            net = (sums.get('inflow') or Decimal(0)) - (sums.get('outflow') or Decimal(0))
        except Exception:
            net = Decimal(0)
        ctx['stats'] = {
            'count': sums.get('total_count') or 0,
            'inflow': sums.get('inflow') or Decimal(0),
            'outflow': sums.get('outflow') or Decimal(0),
            'net': net,
        }
        return ctx


class IncomeCreateView(CreateView):
    model = FinanceTransaction
    form_class = FinanceTransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('finance:transactions_list')

    def get_initial(self):
        initial = super().get_initial()
        note = self.request.GET.get('note') or self.request.GET.get('note_prefill')
        if note:
            initial['note'] = note
        # Preselect customer from GET: support id or customer code
        cust_param = (self.request.GET.get('customer') or '').strip()
        if cust_param:
            obj = None
            if cust_param.isdigit():
                obj = Customer.objects.filter(id=int(cust_param)).first()
            if obj is None:
                obj = Customer.objects.filter(code=cust_param).first()
            if obj:
                initial['customer'] = obj.id
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = FinanceCategory.objects.filter(type='INCOME').order_by('name')
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Thêm khoản thu - NavyBaby'
        ctx['view_type'] = 'income'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Đã thêm khoản thu!')
        return super().form_valid(form)


class ExpenseCreateView(CreateView):
    model = FinanceTransaction
    form_class = FinanceTransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('finance:transactions_list')

    def get_initial(self):
        initial = super().get_initial()
        note = self.request.GET.get('note') or self.request.GET.get('note_prefill')
        if note:
            initial['note'] = note
        # Preselect customer from GET: support id or customer code
        cust_param = (self.request.GET.get('customer') or '').strip()
        if cust_param:
            obj = None
            if cust_param.isdigit():
                obj = Customer.objects.filter(id=int(cust_param)).first()
            if obj is None:
                obj = Customer.objects.filter(code=cust_param).first()
            if obj:
                initial['customer'] = obj.id
        # Prefill category by id or by name (case-insensitive)
        cat_id = (self.request.GET.get('category') or '').strip()
        cat_name = (self.request.GET.get('category_name') or '').strip()
        cat_obj = None
        try:
            if cat_id.isdigit():
                cat_obj = FinanceCategory.objects.filter(id=int(cat_id), type='EXPENSE').first()
        except Exception:
            cat_obj = None
        if cat_obj is None and cat_name:
            cat_obj = FinanceCategory.objects.filter(type='EXPENSE', name__iexact=cat_name).first()
        if cat_obj:
            initial['category'] = cat_obj.id
        # Prefill amount if provided
        amt = (self.request.GET.get('amount') or '').strip()
        try:
            if amt:
                # accept int/float strings
                initial['amount'] = float(amt)
        except Exception:
            pass
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = FinanceCategory.objects.filter(type='EXPENSE').order_by('name')
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Thêm khoản chi - NavyBaby'
        ctx['view_type'] = 'expense'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Đã thêm khoản chi!')
        return super().form_valid(form)


class TransactionUpdateView(UpdateView):
    model = FinanceTransaction
    form_class = FinanceTransactionForm
    template_name = 'finance/transaction_form.html'

    def get_success_url(self):
        return reverse_lazy('finance:transactions_list')

    def form_valid(self, form):
        messages.success(self.request, 'Đã cập nhật giao dịch!')
        return super().form_valid(form)


class TransactionDeleteView(DeleteView):
    model = FinanceTransaction
    template_name = 'finance/transaction_confirm_delete.html'
    success_url = reverse_lazy('finance:transactions_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Đã xóa giao dịch!')
        return super().delete(request, *args, **kwargs)
