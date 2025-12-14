from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Sum, F, FloatField, IntegerField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator

from .models import Product, Category, Supplier
from orders.models import Order
from .forms import ProductForm


class ProductListView(ListView):
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = (
            Product.objects
            .select_related('category', 'supplier')
            .prefetch_related('colors', 'sizes')
            .annotate(
                order_count=Coalesce(Count('orders'), 0, output_field=IntegerField()),
            )
        )
        # Exclude cancelled orders from revenue aggregation
        from django.db.models import Case, When, Value
        revenue_term = ExpressionWrapper(F('orders__amount') * F('price'), output_field=FloatField())
        queryset = queryset.annotate(
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
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by supplier
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'created_asc':
            queryset = queryset.order_by('created_at')
        elif sort == 'price_asc':
            queryset = queryset.order_by('price', '-created_at')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price', '-created_at')
        elif sort == 'orders_asc':
            queryset = queryset.order_by('order_count', '-created_at')
        elif sort == 'orders_desc':
            queryset = queryset.order_by('-order_count', '-created_at')
        elif sort == 'revenue_asc':
            queryset = queryset.order_by('total_revenue', '-created_at')
        elif sort == 'revenue_desc':
            queryset = queryset.order_by('-total_revenue', '-created_at')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Danh sách sản phẩm - NavyBaby'
        categories_qs = Category.objects.all()
        suppliers_qs = Supplier.objects.all()
        context['categories'] = categories_qs
        context['suppliers'] = suppliers_qs
        context['search_query'] = self.request.GET.get('q', '')
        sel_cat = (self.request.GET.get('category', '') or '').strip()
        sel_sup = (self.request.GET.get('supplier', '') or '').strip()
        # Validate category id
        if sel_cat:
            try:
                cat_id = int(sel_cat)
                if not categories_qs.filter(id=cat_id).exists():
                    sel_cat = ''
            except (TypeError, ValueError):
                sel_cat = ''
        # Validate supplier id
        if sel_sup:
            try:
                sup_id = int(sel_sup)
                if not suppliers_qs.filter(id=sup_id).exists():
                    sel_sup = ''
            except (TypeError, ValueError):
                sel_sup = ''
        context['selected_category'] = sel_cat
        context['selected_supplier'] = sel_sup
        context['display'] = self.request.GET.get('display', 'table')
        context['sort'] = self.request.GET.get('sort', 'created_desc')
        # Placeholder: profit could be computed if cost fields exist; keep None for now
        context['has_profit'] = False
        return context


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/create.html'
    success_url = reverse_lazy('products:product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thêm sản phẩm mới - NavyBaby'
        context['action'] = 'create'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Sản phẩm đã được thêm thành công!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Vui lòng kiểm tra lại thông tin sản phẩm.')
        return super().form_invalid(form)


class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/create.html'
    
    def get_success_url(self):
        return reverse_lazy('products:product_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Cập nhật sản phẩm: {self.object.name} - NavyBaby'
        context['action'] = 'update'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Thông tin sản phẩm đã được cập nhật!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Vui lòng kiểm tra lại thông tin sản phẩm.')
        return super().form_invalid(form)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'{self.object.name} - Chi tiết sản phẩm - NavyBaby'

        # Stats for this product (zero-out cancelled)
        from django.db.models import F, FloatField, IntegerField, ExpressionWrapper, Case, When, Value
        from django.db.models.functions import Coalesce
        total_orders = Order.objects.filter(product=self.object).count()
        stats_qs = (
            Order.objects.filter(product=self.object)
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
        stats_agg = stats_qs.aggregate(
            total_discount=Coalesce(Sum('discount_safe'), 0.0),
            total_revenue=Coalesce(Sum('revenue'), 0.0),
        )
        context['stats'] = {
            'order_count': total_orders,
            'total_discount': stats_agg.get('total_discount') or 0,
            'revenue': stats_agg.get('total_revenue') or 0,
        }

        # Recent orders for this product with search/filter/sort (mirroring orders list behavior)
        # Base queryset
        qs = (
            Order.objects
            .filter(product=self.object)
            .select_related('customer', 'product', 'color', 'size')
        )

        # Search: support both 'q' and 'search'
        search_query = (self.request.GET.get('q') or self.request.GET.get('search') or '').strip()
        if search_query:
            qs = qs.filter(
                Q(code__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(status__icontains=search_query)
            )

        # Status filter (multi-select)
        status_list = self.request.GET.getlist('status')
        if status_list:
            qs = qs.filter(status__in=status_list)

        # Color and Size filters
        color_filter = (self.request.GET.get('color') or '').strip()
        size_filter = (self.request.GET.get('size') or '').strip()
        if color_filter:
            qs = qs.filter(color_id=color_filter)
        if size_filter:
            qs = qs.filter(size_id=size_filter)

        # Date range filters (created_at date)
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # Annotations (revenue/net_profit like orders list, zero-out when cancelled)
        from django.db.models import Case, When, Value
        qs = qs.annotate(
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
            qs = qs.order_by('revenue', '-updated_at')
        elif sort == 'revenue_desc':
            qs = qs.order_by('-revenue', '-updated_at')
        elif sort == 'created_asc':
            qs = qs.order_by('created_at')
        elif sort == 'created_desc':
            qs = qs.order_by('-created_at')
        elif sort == 'updated_asc':
            qs = qs.order_by('updated_at')
        else:
            # Default: newest updated first
            qs = qs.order_by('-updated_at')

        recent_orders = qs
        context['recent_orders'] = recent_orders

        # Aggregates for the (filtered) list
        list_aggs = qs.aggregate(
            order_count=Count('id'),
            total_amount=Coalesce(Sum('amount_safe'), 0, output_field=IntegerField()),
            total_discount=Coalesce(Sum('discount_safe'), 0.0, output_field=FloatField()),
            total_revenue=Coalesce(Sum('revenue'), 0.0, output_field=FloatField()),
        )
        list_aggs['total_net_profit'] = (list_aggs.get('total_revenue') or 0) - (list_aggs.get('total_discount') or 0)
        context['list_totals'] = list_aggs

        # Additional context for filters UI
        context['status_choices'] = dict(Order.STATUS_CHOICES)
        context['search_query'] = self.request.GET.get('q', self.request.GET.get('search', ''))
        # Default sorting: newest updated first
        context['sort'] = self.request.GET.get('sort', 'updated_desc')
        context['status_filter'] = status_list
        context['color_filter'] = color_filter
        context['size_filter'] = size_filter
        context['date_from'] = date_from or ''
        context['date_to'] = date_to or ''

        return context


class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'products/confirm_delete.html'
    success_url = reverse_lazy('products:product_list')
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Sản phẩm đã được xóa thành công!')
        return response


class ProductReportView(DetailView):
    model = Product
    template_name = 'products/report.html'
    context_object_name = 'product'

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
        from django.utils import timezone
        from django.utils.safestring import mark_safe
        import json

        context = super().get_context_data(**kwargs)
        product = self.object

        context['title'] = f"Báo cáo sản phẩm {product.name} - NavyBaby"

        # Date range: default from product.created_at to today
        date_format = '%Y-%m-%d'
        product_created_date = product.created_at.date()
        today = timezone.localdate()

        start_param = self.request.GET.get('start')
        end_param = self.request.GET.get('end')

        start_date = product_created_date
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

        # Clamp to valid bounds
        if start_date < product_created_date:
            start_date = product_created_date
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
            .filter(product=product, created_at__date__gte=start_date, created_at__date__lte=end_date)
            .select_related('customer')
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

        # Orders per day within date range
        orders_per_day_qs = (
            orders_qs
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(order_count=Count('id'))
        )
        counts_by_day = {row['day']: row['order_count'] or 0 for row in orders_per_day_qs}

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

        # Top customers by net profit (aggregate by customer)
        top_customers_qs = (
            annotated_qs
            .values('customer_id')
            .annotate(
                customer_name=F('customer__name'),
                customer_code=F('customer__code'),
                total_net_profit=Sum('net_profit'),
                order_count=Count('id'),
                total_amount=Coalesce(Sum('amount_safe'), 0, output_field=IntegerField()),
            )
            .order_by('-total_net_profit')[:10]
        )
        top_customers_list = list(top_customers_qs)
        context['top_customers'] = top_customers_list

        # JSON-friendly data for chart
        top_customers_chart = []
        for row in top_customers_list:
            customer_id = row.get('customer_id')
            customer_code = row.get('customer_code') or f"KH-{customer_id}"
            code = customer_code
            name = row.get('customer_name') or '(Không tên)'
            order_cnt = row.get('order_count') or 0
            total_amt = row.get('total_amount') or 0
            net_rev = row.get('total_net_profit') or 0

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
            top_customers_chart.append({
                'customer_id': customer_id,
                'customer_code': customer_code,
                'code': code,
                'name': name,
                'order_count': order_cnt,
                'total_amount': total_amt,
                'net_revenue': net_rev,
            })

        context['top_customers_chart'] = mark_safe(json.dumps(top_customers_chart))

        return context
