from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('san-pham', views.ProductListView.as_view(), name='product_list'),
    path('san-pham/tao-moi', views.ProductCreateView.as_view(), name='product_create'),
    path('san-pham/<int:pk>', views.ProductDetailView.as_view(), name='product_detail'),
    path('san-pham/<int:pk>/bao-cao', views.ProductReportView.as_view(), name='product_report'),
    path('san-pham/<int:pk>/cap-nhat', views.ProductUpdateView.as_view(), name='product_update'),
    path('san-pham/<int:pk>/xoa', views.ProductDeleteView.as_view(), name='product_delete'),
]
