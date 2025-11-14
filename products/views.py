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
            qs = qs.order_by('revenue', '-created_at')
        elif sort == 'revenue_desc':
            qs = qs.order_by('-revenue', '-created_at')
        elif sort == 'created_asc':
            qs = qs.order_by('created_at')
        else:
            qs = qs.order_by('-created_at')

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
        context['sort'] = self.request.GET.get('sort', 'created_desc')
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
