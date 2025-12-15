from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    # Wallet URLs
    path('', views.wallet_list, name='wallet_list'),
    path('tao-vi/', views.wallet_create, name='wallet_create'),
    path('<int:wallet_id>/', views.wallet_detail, name='wallet_detail'),
    path('<int:wallet_id>/bao-cao/', views.wallet_report, name='wallet_report'),
    path('<int:wallet_id>/chinh-sua/', views.wallet_edit, name='wallet_edit'),
    path('<int:wallet_id>/xoa/', views.wallet_delete, name='wallet_delete'),
    
    # Transaction URLs
    path('<int:wallet_id>/giao-dich/them/', views.transaction_create, name='transaction_create'),
    path('giao-dich/<int:transaction_id>/chinh-sua/', views.transaction_edit, name='transaction_edit'),
    path('giao-dich/<int:transaction_id>/xoa/', views.transaction_delete, name='transaction_delete'),
]
