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

        # Get custom date range from GET parameters
        start_date_str = self.request.GET.get('start_date', '')
        end_date_str = self.request.GET.get('end_date', '')
        
        # Parse dates
        custom_start_date = None
        custom_end_date = None
        
        if start_date_str:
            try:
                custom_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                context['start_date'] = start_date_str
            except ValueError:
                pass
        
        if end_date_str:
            try:
                custom_end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                context['end_date'] = end_date_str
            except ValueError:
                pass

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
        
        # Determine date range for charts based on custom dates or defaults
        if custom_start_date and custom_end_date:
            chart_start = timezone.make_aware(datetime.combine(custom_start_date, datetime.min.time()))
            chart_end = timezone.make_aware(datetime.combine(custom_end_date, datetime.max.time()))
            date_range_label = f"từ {start_date_str} đến {end_date_str}"
        elif custom_start_date:
            chart_start = timezone.make_aware(datetime.combine(custom_start_date, datetime.min.time()))
            chart_end = now
            date_range_label = f"từ {start_date_str}"
        elif custom_end_date:
            chart_start = start_month  # Default to start of month if only end date provided
            chart_end = timezone.make_aware(datetime.combine(custom_end_date, datetime.max.time()))
            date_range_label = f"đến {end_date_str}"
        else:
            # Default: last 30 days for timeline, current month for top products/customers
            chart_start = start_today - timedelta(days=30)
            chart_end = now
            date_range_label = "30 ngày qua"
        
        context['date_range_label'] = date_range_label

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

        # Top-selling products (by net revenue) - use custom date range or current month
        from django.db.models import Case, When, Value, FloatField
        top_products_start = chart_start if (custom_start_date or custom_end_date) else start_month
        top_products_qs = (
            Order.objects
            .exclude(status__in=['reconciled', 'cancelled'])
            .filter(created_at__gte=top_products_start, created_at__lte=chart_end)
            .select_related('product')
            .values('product_id', 'product__name', 'product__code')
            .annotate(
                order_count=Coalesce(Sum(Case(When(id__isnull=False, then=1), default=0, output_field=IntegerField())), 0),
                total_amount=Coalesce(Sum('amount'), 0),
                net_revenue=Coalesce(Sum(order_value_expr), 0),
            )
            .order_by('-net_revenue')[:10]
        )
        context['top_products'] = list(top_products_qs)

        # Top customers (by net revenue) - use custom date range or current month
        top_customers_start = chart_start if (custom_start_date or custom_end_date) else start_month
        top_customers_qs = (
            Order.objects
            .exclude(status__in=['reconciled', 'cancelled'])
            .filter(created_at__gte=top_customers_start, created_at__lte=chart_end)
            .select_related('customer')
            .values('customer_id', 'customer__name', 'customer__code')
            .annotate(
                order_count=Coalesce(Sum(Case(When(id__isnull=False, then=1), default=0, output_field=IntegerField())), 0),
                total_amount=Coalesce(Sum('amount'), 0),
                net_revenue=Coalesce(Sum(order_value_expr), 0),
            )
            .order_by('-net_revenue')[:10]
        )
        context['top_customers'] = list(top_customers_qs)

        # Order status breakdown - use custom date range or current month
        from django.db.models import Count
        status_breakdown_start = chart_start if (custom_start_date or custom_end_date) else start_month
        status_breakdown_qs = (
            Order.objects
            .filter(created_at__gte=status_breakdown_start, created_at__lte=chart_end)
            .values('status')
            .annotate(
                order_count=Count('id'),
                total_revenue=Coalesce(Sum(order_value_expr), 0),
            )
            .order_by('-order_count')
        )
        status_map = dict(Order.STATUS_CHOICES)
        status_breakdown = []
        for row in status_breakdown_qs:
            status_breakdown.append({
                'status': row['status'],
                'label': status_map.get(row['status'], row['status']),
                'order_count': row['order_count'],
                'total_revenue': row['total_revenue'],
            })
        context['status_breakdown'] = status_breakdown

        # Revenue timeline (daily) - use custom date range or last 30 days
        from django.db.models.functions import TruncDate
        daily_revenue_qs = (
            Order.objects
            .exclude(status__in=['reconciled', 'cancelled'])
            .filter(created_at__gte=chart_start, created_at__lte=chart_end)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                order_count=Count('id'),
                revenue=Coalesce(Sum(order_value_expr), 0),
            )
            .order_by('day')
        )
        revenue_by_day = {row['day']: {'count': row['order_count'], 'revenue': row['revenue']} for row in daily_revenue_qs}
        
        # Fill missing days with 0
        revenue_timeline = []
        current_day = chart_start.date()
        end_day = chart_end.date()
        while current_day <= end_day:
            data = revenue_by_day.get(current_day, {'count': 0, 'revenue': 0})
            revenue_timeline.append({
                'day': current_day.strftime('%Y-%m-%d'),
                'order_count': data['count'],
                'revenue': data['revenue'],
            })
            current_day += timedelta(days=1)
        context['revenue_timeline'] = revenue_timeline

        # Serialize data for charts with additional info
        import json
        from django.utils.safestring import mark_safe
        
        # Enrich top products with image URLs
        top_products_enriched = []
        for row in top_products_qs:
            product_id = row.get('product_id')
            product_image = ''
            try:
                product_obj = Product.objects.filter(id=product_id).only('image').first()
                if product_obj and getattr(product_obj, 'image', None):
                    try:
                        product_image = self.request.build_absolute_uri(product_obj.image.url)
                    except Exception:
                        product_image = str(product_obj.image) if product_obj.image else ''
            except Exception:
                pass
            
            enriched = dict(row)
            enriched['image'] = product_image
            top_products_enriched.append(enriched)
        
        context['top_products_chart'] = mark_safe(json.dumps(top_products_enriched))
        context['top_customers_chart'] = mark_safe(json.dumps(list(top_customers_qs)))
        context['status_breakdown_chart'] = mark_safe(json.dumps(status_breakdown))
        context['revenue_timeline_chart'] = mark_safe(json.dumps(revenue_timeline))

        return context
