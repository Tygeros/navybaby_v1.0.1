from decimal import Decimal

from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from .models import Customer
from django.views.generic.edit import UpdateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from orders.models import Order
from finance.models import FinanceTransaction
from django.db import models


class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        from django.db.models import Q, Count, Sum, F, FloatField, IntegerField, ExpressionWrapper, Case, When, Value
        from django.db.models.functions import Coalesce

        qs = (
            Customer.objects
            .annotate(
                total_orders=Coalesce(Count('orders', distinct=True), 0, output_field=IntegerField()),
                total_discount=Coalesce(
                    Sum(
                        Case(
                            When(orders__status='cancelled', then=Value(0.0)),
                            default=F('orders__discount'),
                            output_field=FloatField(),
                        ),
                        output_field=FloatField(),
                    ),
                    0.0,
                    output_field=FloatField(),
                ),
            )
        )

        revenue_term = ExpressionWrapper(F('orders__amount') * F('orders__sale_price'), output_field=FloatField())
        qs = qs.annotate(
            total_revenue=Coalesce(
                Sum(
                    Case(
                        When(orders__status='cancelled', then=Value(0.0)),
                        default=revenue_term,
                        output_field=FloatField(),
                    ),
                    output_field=FloatField(),
                ),
                0.0,
                output_field=FloatField(),
            )
        )
        qs = qs.annotate(net_profit=ExpressionWrapper(F('total_revenue') - F('total_discount'), output_field=FloatField()))

        # Search
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(phone_number__icontains=q))

        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'revenue_asc':
            qs = qs.order_by('total_revenue', '-created_at')
        elif sort == 'revenue_desc':
            qs = qs.order_by('-total_revenue', '-created_at')
        elif sort == 'created_asc':
            qs = qs.order_by('created_at')
        else:
            qs = qs.order_by('-created_at')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        display = self.request.GET.get('display', 'table')
        if display not in ['table', 'card']:
            display = 'table'
        context['display'] = display
        context['title'] = 'Khách hàng - NavyBaby'
        context['search_query'] = self.request.GET.get('q', '')
        context['sort'] = self.request.GET.get('sort', 'created_desc')
        return context


class CustomerCreateView(CreateView):
    model = Customer
    template_name = 'customers/create.html'
    fields = ['code', 'name', 'phone_number', 'social_link', 'address', 'is_affiliate', 'note']
    success_url = reverse_lazy('customers:customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thêm khách hàng - NavyBaby'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        base_classes = 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700'
        for name, field in form.fields.items():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if name == 'is_affiliate':
                # keep checkbox default minimal styling
                widget.attrs['class'] = existing
            else:
                widget.attrs['class'] = (existing + ' ' + base_classes).strip()
            if name == 'code':
                field.required = False
                widget.attrs['placeholder'] = 'Mã KH (để trống sẽ tự tạo)'
        return form


class CustomerDetailView(DetailView):
    model = Customer
    template_name = 'customers/detail.html'
    context_object_name = 'customer'
    slug_field = 'code'
    slug_url_kwarg = 'code'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Khách hàng {self.object.name} - NavyBaby"
        # Compute stats and recent orders with filters/sort/search
        from django.db.models import F, FloatField, IntegerField, ExpressionWrapper, Sum, Case, When, Value
        from django.db.models.functions import Coalesce

        base_qs = Order.objects.filter(customer=self.object).select_related('product')

        # Filtering by multiple status
        status_list = self.request.GET.getlist('status')
        if status_list:
            base_qs = base_qs.filter(status__in=status_list)

        # Filtering by multiple suppliers
        supplier_ids = self.request.GET.getlist('supplier')
        if supplier_ids:
            base_qs = base_qs.filter(product__supplier_id__in=supplier_ids)

        # Searching by code or product name
        q = self.request.GET.get('q')
        if q:
            base_qs = base_qs.filter(models.Q(code__icontains=q) | models.Q(product__name__icontains=q))

        # Annotate revenue/discount; zero-out when cancelled
        annotated_qs = base_qs.annotate(
            amount_safe=Coalesce(F('amount'), 0, output_field=IntegerField()),
            price_safe=Coalesce(F('sale_price'), 0.0, output_field=FloatField()),
        ).annotate(
            discount_raw=Coalesce(F('discount'), 0.0, output_field=FloatField()),
            revenue_raw=ExpressionWrapper(F('amount_safe') * F('price_safe'), output_field=FloatField()),
        ).annotate(
            discount_safe=Case(
                When(status='cancelled', then=Value(0.0)),
                default=F('discount_raw'),
                output_field=FloatField(),
            ),
            revenue=Case(
                When(status='cancelled', then=Value(0.0)),
                default=F('revenue_raw'),
                output_field=FloatField(),
            ),
        ).annotate(
            net_profit=ExpressionWrapper(F('revenue') - F('discount_safe'), output_field=FloatField())
        )

        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'revenue_asc':
            annotated_qs = annotated_qs.order_by('revenue', '-created_at')
        elif sort == 'revenue_desc':
            annotated_qs = annotated_qs.order_by('-revenue', '-created_at')
        elif sort == 'created_asc':
            annotated_qs = annotated_qs.order_by('created_at')
        else:
            # default newest first
            annotated_qs = annotated_qs.order_by('-created_at')

        recent_orders = list(annotated_qs)

        # Aggregates for the (filtered) list
        list_aggs = annotated_qs.aggregate(
            order_count=models.Count('id'),
            total_amount=Coalesce(Sum('amount_safe'), 0, output_field=IntegerField()),
            total_discount=Coalesce(Sum('discount_safe'), 0.0, output_field=FloatField()),
            total_revenue=Coalesce(Sum('revenue'), 0.0, output_field=FloatField()),
        )
        list_aggs['total_net_profit'] = (list_aggs.get('total_revenue') or 0) - (list_aggs.get('total_discount') or 0)

        # Stats are always computed from all customer's orders (not filtered), zero-out if cancelled
        stats_qs = (
            Order.objects
            .filter(customer=self.object)
            .select_related('product')
            .annotate(
                amount_safe=Coalesce(F('amount'), 0, output_field=IntegerField()),
                price_safe=Coalesce(F('sale_price'), 0.0, output_field=FloatField()),
            )
            .annotate(
                discount_raw=Coalesce(F('discount'), 0.0, output_field=FloatField()),
                revenue_raw=ExpressionWrapper(F('amount_safe') * F('price_safe'), output_field=FloatField()),
            )
            .annotate(
                discount_safe=Case(
                    When(status='cancelled', then=Value(0.0)),
                    default=F('discount_raw'),
                    output_field=FloatField(),
                ),
                revenue=Case(
                    When(status='cancelled', then=Value(0.0)),
                    default=F('revenue_raw'),
                    output_field=FloatField(),
                ),
            )
        )
        order_count = stats_qs.count()
        stats_agg = stats_qs.aggregate(
            total_discount=Coalesce(Sum('discount_safe'), 0.0),
            total_revenue=Coalesce(Sum('revenue'), 0.0),
        )
        total_discount_val = stats_agg.get('total_discount') or 0
        revenue_val = stats_agg.get('total_revenue') or 0
        net_profit_val = (revenue_val or 0) - (total_discount_val or 0)

        def format_currency(v):
            try:
                return f"{int(v):,}đ".replace(",", ".")
            except Exception:
                return f"{v}đ"

        context['stats'] = {
            'order_count': order_count,
            'total_discount': format_currency(total_discount_val),
            'revenue': format_currency(revenue_val),
            'net_profit': format_currency(net_profit_val),
        }

        transactions_qs = (
            FinanceTransaction.objects
            .filter(customer=self.object)
            .select_related('category')
        )

        zero_decimal = Decimal('0')
        paid_category_names = [
            'KH thanh toán đơn hàng',
            'Khấu trừ khoản tiền đặt cọc',
        ]
        paid_filter = models.Q()
        for name in paid_category_names:
            paid_filter |= models.Q(category__name__iexact=name)
        if paid_filter.children:
            paid_total = transactions_qs.filter(paid_filter).aggregate(total=Sum('amount')).get('total')
        else:
            paid_total = zero_decimal
        paid_total = Decimal(paid_total or zero_decimal)

        deposit_effective_name = 'KH đặt cọc tiền hàng'
        deposit_deducted_name = 'Khấu trừ khoản tiền đặt cọc'
        deposit_effective = (
            transactions_qs
            .filter(category__name__iexact=deposit_effective_name)
            .aggregate(total=Sum('amount'))
            .get('total')
            or zero_decimal
        )
        deposit_deducted = (
            transactions_qs
            .filter(category__name__iexact=deposit_deducted_name)
            .aggregate(total=Sum('amount'))
            .get('total')
            or zero_decimal
        )
        deposit_total = Decimal(deposit_effective or zero_decimal) - Decimal(deposit_deducted or zero_decimal)

        net_profit_decimal = Decimal(net_profit_val or 0)
        remaining_total = net_profit_decimal - paid_total - deposit_total
        # Paid display should be total net profit of reconciled orders
        reconciled_agg = (
            stats_qs
            .filter(status='reconciled')
            .aggregate(
                total_discount=Coalesce(Sum('discount_safe'), 0.0),
                total_revenue=Coalesce(Sum('revenue'), 0.0),
            )
        )
        reconciled_net_val = (reconciled_agg.get('total_revenue') or 0) - (reconciled_agg.get('total_discount') or 0)
        try:
            reconciled_net_decimal = Decimal(str(reconciled_net_val or 0))
        except Exception:
            reconciled_net_decimal = Decimal('0')
        # Update remaining to follow: net_profit - paid(display) - deposit
        remaining_total = net_profit_decimal - reconciled_net_decimal - deposit_total

        context['payment_summary'] = {
            'paid': format_currency(reconciled_net_decimal),
            'deposit': format_currency(deposit_total),
            'remaining': format_currency(remaining_total),
        }
        # raw numbers for building URLs
        try:
            paid_int = int(reconciled_net_decimal)
        except Exception:
            paid_int = 0
        try:
            deposit_int = int(deposit_total)
        except Exception:
            deposit_int = 0
        try:
            remaining_int = int(remaining_total)
        except Exception:
            remaining_int = 0
        context['payment_raw'] = {
            'paid': paid_int,
            'deposit': deposit_int,
            'remaining': remaining_int,
        }
        context['recent_orders'] = recent_orders
        context['list_totals'] = list_aggs
        context['order_status_choices'] = Order.STATUS_CHOICES
        # Suppliers list for filter
        try:
            from suppliers.models import Supplier
            context['suppliers'] = Supplier.objects.all()
        except Exception:
            context['suppliers'] = []
        context['current_filters'] = {
            'status': status_list,
            'supplier': supplier_ids,
            'q': q or '',
            'sort': sort or 'created_desc',
        }
        return context


class CustomerUpdateView(UpdateView):
    model = Customer
    template_name = 'customers/update.html'
    context_object_name = 'customer'
    slug_field = 'code'
    slug_url_kwarg = 'code'
    fields = ['name', 'phone_number', 'social_link', 'address', 'is_affiliate', 'note']

    def get_success_url(self):
        return reverse_lazy('customers:customer_detail', kwargs={'code': self.object.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Chỉnh sửa khách hàng {self.object.name} - NavyBaby"
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        base_classes = 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700'
        for name, field in form.fields.items():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if name == 'is_affiliate':
                widget.attrs['class'] = existing
            else:
                widget.attrs['class'] = (existing + ' ' + base_classes).strip()
        return form


class DeleteCustomerView(View):
    def post(self, request, code):
        customer = get_object_or_404(Customer, code=code)
        customer.delete()
        return redirect('customers:customer_list')


class CustomerBillView(DetailView):
    model = Customer
    template_name = 'customers/bill.html'
    context_object_name = 'customer'
    slug_field = 'code'
    slug_url_kwarg = 'code'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = self.object

        from django.db.models import F, FloatField, IntegerField, ExpressionWrapper, Case, When, Value
        from django.db.models.functions import Coalesce
        from django.db import models

        qs = Order.objects.filter(customer=customer).select_related('product', 'color', 'size')

        # Apply same filters as detail
        status_list = self.request.GET.getlist('status')
        if status_list:
            qs = qs.filter(status__in=status_list)
        supplier_ids = self.request.GET.getlist('supplier')
        if supplier_ids:
            qs = qs.filter(product__supplier_id__in=supplier_ids)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(models.Q(code__icontains=q) | models.Q(product__name__icontains=q))

        annotated = (
            qs
            .annotate(
                amount_safe=Coalesce(F('amount'), 0, output_field=IntegerField()),
                price_safe=Coalesce(F('sale_price'), 0.0, output_field=FloatField()),
            )
            .annotate(
                discount_raw=Coalesce(F('discount'), 0.0, output_field=FloatField()),
                revenue_raw=ExpressionWrapper(F('amount_safe') * F('price_safe'), output_field=FloatField()),
            )
            .annotate(
                discount_safe=Case(
                    When(status='cancelled', then=Value(0.0)),
                    default=F('discount_raw'),
                    output_field=FloatField(),
                ),
                revenue=Case(
                    When(status='cancelled', then=Value(0.0)),
                    default=F('revenue_raw'),
                    output_field=FloatField(),
                ),
            )
            .annotate(
                net_profit=ExpressionWrapper(F('revenue') - F('discount_safe'), output_field=FloatField())
            )
            .annotate(
                unit_price=Case(
                    When(amount_safe=0, then=Value(0.0)),
                    default=ExpressionWrapper(F('net_profit') / F('amount_safe'), output_field=FloatField()),
                    output_field=FloatField(),
                )
            )
        )

        sort = self.request.GET.get('sort')
        if sort == 'revenue_asc':
            annotated = annotated.order_by('net_profit', '-created_at')
        elif sort == 'revenue_desc':
            annotated = annotated.order_by('-net_profit', '-created_at')
        elif sort == 'created_asc':
            annotated = annotated.order_by('created_at')
        else:
            annotated = annotated.order_by('-created_at')

        orders = list(annotated)

        # Totals
        total_goods = 0.0
        for o in orders:
            try:
                total_goods += float(getattr(o, 'net_profit', 0) or 0)
            except Exception:
                pass

        # Paid amount on bill: allow override via GET ?paid_override=...
        paid_override = self.request.GET.get('paid_override')
        paid_amount_val = None
        if paid_override is not None:
            try:
                paid_amount_val = int(float(paid_override))
            except Exception:
                paid_amount_val = None
        if paid_amount_val is None:
            # Default = current deposit balance (like customers/detail.html)
            from django.db.models import Sum as DjSum
            transactions_qs = FinanceTransaction.objects.filter(customer=customer).select_related('category')
            zero_val = 0
            deposit_effective_name = 'KH đặt cọc tiền hàng'
            deposit_deducted_name = 'Khấu trừ khoản tiền đặt cọc'
            deposit_effective = (
                transactions_qs
                .filter(category__name__iexact=deposit_effective_name)
                .aggregate(total=DjSum('amount'))
                .get('total')
                or zero_val
            )
            deposit_deducted = (
                transactions_qs
                .filter(category__name__iexact=deposit_deducted_name)
                .aggregate(total=DjSum('amount'))
                .get('total')
                or zero_val
            )
            paid_amount_val = (deposit_effective or 0) - (deposit_deducted or 0)

        remaining = float(total_goods) - float(paid_amount_val or 0)

        # Build QR URL: allow override via GET ?qr_url=..., else generate simple QR with transfer info
        try:
            from urllib.parse import quote
        except Exception:
            quote = lambda x: x
        bank_name = 'Techcombank'
        bank_owner = 'Quách Thị Phương Nga'
        bank_account = '19036902149010'
        amount_int = int(remaining)
        qr_url = self.request.GET.get('qr_url')
        if not qr_url:
            # Prefer a default Cloudinary URL if provided via env settings
            try:
                from django.conf import settings
                default_cloud_qr = getattr(settings, 'CLOUDINARY_QR_URL', None) or None
            except Exception:
                default_cloud_qr = None
            if default_cloud_qr:
                qr_url = default_cloud_qr
            else:
                # Fallback: generate a simple QR on-the-fly
                qr_payload = (
                    f"Ngân hàng: {bank_name}\n"
                    f"Chủ TK: {bank_owner}\n"
                    f"STK: {bank_account}\n"
                    f"Số tiền: {amount_int}đ\n"
                    f"Nội dung: {customer.code}"
                )
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={quote(qr_payload)}"

        # If admin-uploaded QR selected via ?qr_id, use that instead
        qr_id = self.request.GET.get('qr_id')
        if qr_id and str(qr_id).isdigit():
            try:
                from .models import QRCode
                obj = QRCode.objects.filter(id=int(qr_id)).first()
                if obj and getattr(obj, 'url', ''):
                    qr_url = obj.url
            except Exception:
                pass
        elif not qr_url:
            # No explicit QR; prefer a fixed default id=3, then latest uploaded
            try:
                from .models import QRCode
                preferred = QRCode.objects.filter(id=4).first()
                if preferred and getattr(preferred, 'url', ''):
                    qr_url = preferred.url
                else:
                    latest = QRCode.objects.order_by('-created_at').first()
                    if latest and getattr(latest, 'url', ''):
                        qr_url = latest.url
            except Exception:
                pass

        ctx.update({
            'title': f"Bill - {customer.name}",
            'orders': orders,
            'total_goods': int(total_goods),
            'paid_amount': int(paid_amount_val or 0),
            'remaining_amount': int(remaining),
            'created_date': models.functions.Now(),
            'bank_name': bank_name,
            'bank_owner': bank_owner,
            'bank_account': bank_account,
            'qr_url': qr_url,
        })
        return ctx
