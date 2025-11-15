from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, IntegerField, ExpressionWrapper, Sum
from django.db.models.functions import Coalesce
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
        return context
