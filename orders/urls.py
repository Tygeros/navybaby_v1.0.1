from django.urls import path
from django.views.generic import RedirectView
from django.urls import reverse_lazy

from . import views

app_name = 'orders'

urlpatterns = [
    # Redirect /don-hang/ to order list
    path('don-hang/', RedirectView.as_view(url=reverse_lazy('orders:order_list'), permanent=False)),
    
    # Order list and creation
    path('don-hang/danh-sach/', views.OrderListView.as_view(), name='order_list'),
    path('don-hang/tao-moi/', views.OrderCreateView.as_view(), name='order_create'),
    
    # Order detail, update, and delete
    path('don-hang/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('don-hang/<int:pk>/cap-nhat/', views.OrderUpdateView.as_view(), name='order_update'),
    path('don-hang/<int:pk>/xoa/', views.OrderDeleteView.as_view(), name='order_delete'),
    
    # AJAX endpoints
    path('don-hang/api/product/<int:product_id>/details/', views.get_product_details, name='product_details'),
    path('don-hang/<int:pk>/cap-nhat-trang-thai/', views.update_order_status, name='update_order_status'),
    path('don-hang/cap-nhat-trang-thai-nhieu/', views.bulk_update_order_status, name='bulk_update_order_status'),
]
