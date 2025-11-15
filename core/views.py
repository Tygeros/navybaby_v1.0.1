from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, IntegerField, ExpressionWrapper, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from customers.models import Customer
from products.models import Product
from orders.models import Order

class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add default values for all template variables
        context['title'] = 'Bảng điều khiển - NavyBaby'
        context['total_customers'] = Customer.objects.count()
        context['total_products'] = Product.objects.count()
        context['total_orders'] = Order.objects.count()
        context['recent_orders'] = []
        context['top_products'] = []

        # Lãi ròng ước tính
        # - Loại trừ trạng thái: Đã đối soát (reconciled), Hủy đơn (cancelled)
        # - Bỏ qua đơn có product.purchase_price = 0
        # - Lãi thuần mỗi đơn = sale_price * amount - discount - product.purchase_price
        # - Tổng tất cả đơn hợp lệ
        orders_qs = (
            Order.objects
            .exclude(status__in=['reconciled', 'cancelled'])
            .select_related('product')
            .filter(product__purchase_price__gt=0)
        )
        profit_expr = ExpressionWrapper(
            Coalesce(F('sale_price'), 0) * Coalesce(F('amount'), 0)
            - Coalesce(F('discount'), 0)
            - F('product__purchase_price'),
            output_field=IntegerField(),
        )
        context['net_profit'] = orders_qs.aggregate(total=Coalesce(Sum(profit_expr), 0))['total']

        # ===== Period-based statistics for charts =====
        now = timezone.now()
        today_date = timezone.localdate()
        start_today = timezone.make_aware(datetime.combine(today_date, datetime.min.time()))
        start_yesterday = start_today - timedelta(days=1)
        end_yesterday = start_today

        # Week: assume Monday as start of week
        weekday = today_date.weekday()  # Monday=0
        start_week = timezone.make_aware(datetime.combine(today_date - timedelta(days=weekday), datetime.min.time()))
        prev_week_start = start_week - timedelta(days=7)
        prev_week_end = start_week

        # Month boundaries
        start_month = timezone.make_aware(datetime(today_date.year, today_date.month, 1))
        # Previous month start and end
        if today_date.month == 1:
            prev_month_start_date = datetime(today_date.year - 1, 12, 1)
        else:
            prev_month_start_date = datetime(today_date.year, today_date.month - 1, 1)
        prev_month_start = timezone.make_aware(prev_month_start_date)
        prev_month_end = start_month

        # Common filters/helpers
        def in_range(model_qs, field, start, end=None):
            qs = model_qs.filter(**{f"{field}__gte": start})
            if end is not None:
                qs = qs.filter(**{f"{field}__lt": end})
            return qs

        # Customers
        customers_all = Customer.objects.all()
        customer_stats = {
            'today': in_range(customers_all, 'created_at', start_today).count(),
            'yesterday': in_range(customers_all, 'created_at', start_yesterday, end_yesterday).count(),
            'this_week': in_range(customers_all, 'created_at', start_week).count(),
            'last_week': in_range(customers_all, 'created_at', prev_week_start, prev_week_end).count(),
            'this_month': in_range(customers_all, 'created_at', start_month).count(),
            'last_month': in_range(customers_all, 'created_at', prev_month_start, prev_month_end).count(),
        }
        context['customer_stats'] = customer_stats

        # Products
        products_all = Product.objects.all()
        product_stats = {
            'today': in_range(products_all, 'created_at', start_today).count(),
            'yesterday': in_range(products_all, 'created_at', start_yesterday, end_yesterday).count(),
            'this_week': in_range(products_all, 'created_at', start_week).count(),
            'last_week': in_range(products_all, 'created_at', prev_week_start, prev_week_end).count(),
            'this_month': in_range(products_all, 'created_at', start_month).count(),
            'last_month': in_range(products_all, 'created_at', prev_month_start, prev_month_end).count(),
        }
        context['product_stats'] = product_stats

        # Orders (counts and values)
        orders_all = Order.objects.exclude(status__in=['reconciled', 'cancelled'])
        order_value_expr = ExpressionWrapper(
            Coalesce(F('sale_price'), 0) * Coalesce(F('amount'), 0) - Coalesce(F('discount'), 0),
            output_field=IntegerField(),
        )

        def agg_counts_and_values(qs):
            return {
                'count': qs.count(),
                'value': qs.aggregate(total=Coalesce(Sum(order_value_expr), 0))['total']
            }

        orders_today = agg_counts_and_values(in_range(orders_all, 'created_at', start_today))
        orders_yesterday = agg_counts_and_values(in_range(orders_all, 'created_at', start_yesterday, end_yesterday))
        orders_this_week = agg_counts_and_values(in_range(orders_all, 'created_at', start_week))
        orders_last_week = agg_counts_and_values(in_range(orders_all, 'created_at', prev_week_start, prev_week_end))
        orders_this_month = agg_counts_and_values(in_range(orders_all, 'created_at', start_month))
        orders_last_month = agg_counts_and_values(in_range(orders_all, 'created_at', prev_month_start, prev_month_end))

        context['order_stats'] = {
            'today': orders_today,
            'yesterday': orders_yesterday,
            'this_week': orders_this_week,
            'last_week': orders_last_week,
            'this_month': orders_this_month,
            'last_month': orders_last_month,
        }

        # Top-selling products this month (by quantity)
        top_qs = (
            orders_all
            .filter(created_at__gte=start_month)
            .select_related('product')
            .values('product_id', 'product__name')
            .annotate(
                total_amount=Coalesce(Sum('amount'), 0),
                total_value=Coalesce(Sum(order_value_expr), 0),
            )
            .order_by('-total_amount')[:5]
        )
        context['top_products_month'] = list(top_qs)
        return context
