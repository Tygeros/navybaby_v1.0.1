from django.urls import path
from .views import CustomerListView, CustomerCreateView, CustomerDetailView, CustomerUpdateView, DeleteCustomerView, CustomerBillView, CustomerReportView

app_name = 'customers'

urlpatterns = [
    path('khach-hang', CustomerListView.as_view(), name='customer_list'),
    path('khach-hang/tao-moi', CustomerCreateView.as_view(), name='customer_create'),
    path('khach-hang/<slug:code>', CustomerDetailView.as_view(), name='customer_detail'),
    path('khach-hang/<slug:code>/bao-cao', CustomerReportView.as_view(), name='customer_report'),
    path('khach-hang/<slug:code>/bill', CustomerBillView.as_view(), name='customer_bill'),
    path('khach-hang/<slug:code>/chinh-sua', CustomerUpdateView.as_view(), name='customer_update'),
    path('khach-hang/<slug:code>/xoa', DeleteCustomerView.as_view(), name='customer_delete'),
]
