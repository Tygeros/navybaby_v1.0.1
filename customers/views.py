from decimal import Decimal
import json

from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from .models import Customer
from django.views.generic.edit import UpdateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from orders.models import Order
from finance.models import FinanceTransaction
from django.db import models
from django.utils.safestring import mark_safe


class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        from django.db.models import Q, Count, Sum, F, FloatField, IntegerField, ExpressionWrapper, Case, When, Value
        from django.db.models.functions import Coalesce, TruncDate

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
        from django.db.models.functions import Coalesce, TruncDate

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
            annotated_qs = annotated_qs.order_by('revenue', '-updated_at')
        elif sort == 'revenue_desc':
            annotated_qs = annotated_qs.order_by('-revenue', '-updated_at')
        elif sort == 'created_asc':
            annotated_qs = annotated_qs.order_by('created_at')
        elif sort == 'created_desc':
            annotated_qs = annotated_qs.order_by('-created_at')
        elif sort == 'updated_asc':
            annotated_qs = annotated_qs.order_by('updated_at')
        else:
            # default newest updated first
            annotated_qs = annotated_qs.order_by('-updated_at')

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
            # Default sort is by latest update
            'sort': sort or 'updated_desc',
        }
        return context


class CustomerReportView(DetailView):
    model = Customer
    template_name = 'customers/report.html'
    context_object_name = 'customer'
    slug_field = 'code'
    slug_url_kwarg = 'code'

    def get_context_data(self, **kwargs):
        from datetime import datetime, timedelta

        from django.db.models import (
            F,
            FloatField,
            IntegerField,
            ExpressionWrapper,
            Sum,
            Case,
            When,
            Value,
            Count,
        )
        from django.db.models.functions import Coalesce, TruncDate
        from django.db.models import Sum as DjSum
        from django.utils import timezone

        context = super().get_context_data(**kwargs)
        customer = self.object

        context['title'] = f"Báo cáo khách hàng {customer.name} - NavyBaby"

        # Date range: default from customer.created_at to today, overridable via GET ?start=YYYY-MM-DD&end=YYYY-MM-DD
        date_format = '%Y-%m-%d'
        customer_created_date = customer.created_at.date()
        today = timezone.localdate()

        start_param = self.request.GET.get('start')
        end_param = self.request.GET.get('end')

        start_date = customer_created_date
        end_date = today

        if start_param:
            try:
                start_date = datetime.strptime(start_param, date_format).date()
            except Exception:
                pass
        if end_param:
            try:
                end_date = datetime.strptime(end_param, date_format).date()
            except Exception:
                pass

        # Clamp to valid bounds and ensure start <= end
        if start_date < customer_created_date:
            start_date = customer_created_date
        if end_date > today:
            end_date = today
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        context['date_range'] = {
            'start': start_date,
            'end': end_date,
            'start_str': start_date.strftime(date_format),
            'end_str': end_date.strftime(date_format),
        }

        # Orders within date range
        orders_qs = (
            Order.objects
            .filter(customer=customer, created_at__date__gte=start_date, created_at__date__lte=end_date)
            .select_related('product')
        )

        annotated_qs = (
            orders_qs
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
                net_profit=ExpressionWrapper(F('revenue') - F('discount_safe'), output_field=FloatField()),
            )
        )

        order_aggs = annotated_qs.aggregate(
            order_count=Count('id'),
            total_amount=Coalesce(Sum('amount_safe'), 0, output_field=IntegerField()),
            total_discount=Coalesce(Sum('discount_safe'), 0.0, output_field=FloatField()),
            total_revenue=Coalesce(Sum('revenue'), 0.0, output_field=FloatField()),
        )
        total_net_profit = (order_aggs.get('total_revenue') or 0) - (order_aggs.get('total_discount') or 0)
        order_count = order_aggs.get('order_count') or 0
        avg_order_value = total_net_profit / order_count if order_count else 0

        context['order_summary'] = {
            'order_count': order_count,
            'total_amount': order_aggs.get('total_amount') or 0,
            'total_discount': order_aggs.get('total_discount') or 0,
            'total_revenue': order_aggs.get('total_revenue') or 0,
            'total_net_profit': total_net_profit,
            'avg_order_value': avg_order_value,
        }

        # Orders per day within date range (for daily column chart)
        # First aggregate only days that have orders
        orders_per_day_qs = (
            orders_qs
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(order_count=Count('id'))
        )
        counts_by_day = {row['day']: row['order_count'] or 0 for row in orders_per_day_qs}

        # Then build a continuous date range from start_date to end_date,
        # filling missing days with 0 so the chart timeline is accurate.
        days_list = []
        current = start_date
        while current <= end_date:
            days_list.append({
                'day': current,
                'order_count': counts_by_day.get(current, 0),
            })
            current += timedelta(days=1)

        context['orders_per_day'] = days_list

        # Breakdown by order status
        status_map = dict(Order.STATUS_CHOICES)
        status_breakdown_qs = annotated_qs.values('status').annotate(
            order_count=Count('id'),
            total_revenue=Coalesce(Sum('revenue'), 0.0, output_field=FloatField()),
            total_discount=Coalesce(Sum('discount_safe'), 0.0, output_field=FloatField()),
        )
        status_breakdown = []
        for row in status_breakdown_qs:
            revenue_val = row['total_revenue'] or 0
            discount_val = row['total_discount'] or 0
            status_breakdown.append({
                'status': row['status'],
                'label': status_map.get(row['status'], row['status']),
                'order_count': row['order_count'] or 0,
                'total_revenue': revenue_val,
                'total_discount': discount_val,
                'total_net_profit': revenue_val - discount_val,
            })
        context['status_breakdown'] = status_breakdown

        # Top products by net profit (aggregate by product)
        top_products_qs = (
            annotated_qs
            .values('product_id')
            .annotate(
                product_name=F('product__name'),
                product_code=F('product__code'),
                total_net_profit=Sum('net_profit'),
                order_count=Count('id'),
                total_amount=Coalesce(Sum('amount_safe'), 0, output_field=IntegerField()),
            )
            .order_by('-total_net_profit')[:10]
        )
        top_products_list = list(top_products_qs)
        context['top_products'] = top_products_list

        # JSON-friendly data for chart (avoid template logic causing numeric issues)
        top_products_chart = []
        for row in top_products_list:
            product_id = row.get('product_id')
            code = row.get('product_code') or f"SP #{product_id}"
            name = row.get('product_name') or '(Không tên)'
            order_cnt = row.get('order_count') or 0
            total_amt = row.get('total_amount') or 0
            net_rev = row.get('total_net_profit') or 0

            # Get product image (absolute URL so tooltip <img> loads correctly)
            product_image = ''
            try:
                from products.models import Product
                product_obj = Product.objects.filter(id=product_id).only('image').first()
                if product_obj and getattr(product_obj, 'image', None):
                    try:
                        # Prefer full URL based on current request (handles MEDIA_URL automatically)
                        product_image = self.request.build_absolute_uri(product_obj.image.url)
                    except Exception:
                        # Fallback: relative path string
                        product_image = str(product_obj.image)
            except Exception:
                pass

            try:
                order_cnt = int(order_cnt)
            except Exception:
                order_cnt = 0
            try:
                total_amt = int(total_amt)
            except Exception:
                total_amt = 0
            try:
                net_rev = float(net_rev)
            except Exception:
                net_rev = 0.0
            top_products_chart.append({
                'product_id': product_id,
                'code': code,
                'name': name,
                'image': product_image,
                'order_count': order_cnt,
                'total_amount': total_amt,
                'net_revenue': net_rev,
            })

        context['top_products_chart'] = mark_safe(json.dumps(top_products_chart))

        # Finance transactions within date range
        tx_qs = (
            FinanceTransaction.objects
            .filter(customer=customer, created_at__date__gte=start_date, created_at__date__lte=end_date)
            .select_related('category')
        )
        income_total = tx_qs.filter(category__type='INCOME').aggregate(total=DjSum('amount')).get('total') or 0
        expense_total = tx_qs.filter(category__type='EXPENSE').aggregate(total=DjSum('amount')).get('total') or 0
        context['finance_summary'] = {
            'income_total': income_total,
            'expense_total': expense_total,
            'net_cash': (income_total or 0) - (expense_total or 0),
        }
        context['transactions_count'] = tx_qs.count()

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
        bank_name = 'Vietcombank'
        bank_owner = 'Quách Thị Phương Nga'
        bank_account = '9372282552'
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
                preferred = QRCode.objects.filter(id=5).first()
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
