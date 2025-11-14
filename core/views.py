from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
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
        return context
