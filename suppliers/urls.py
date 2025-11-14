from django.urls import path
from .views import (
    SupplierListView,
    SupplierCreateView,
    SupplierUpdateView,
    SupplierDeleteView,
)

app_name = 'suppliers'

urlpatterns = [
    path('nha-cung-cap', SupplierListView.as_view(), name='supplier_list'),
    path('nha-cung-cap/tao-moi', SupplierCreateView.as_view(), name='supplier_create'),
    path('nha-cung-cap/<slug:code>/cap-nhat', SupplierUpdateView.as_view(), name='supplier_update'),
    path('nha-cung-cap/<slug:code>/xoa', SupplierDeleteView.as_view(), name='supplier_delete'),
]
