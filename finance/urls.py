from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Categories
    path('tai-chinh/danh-muc/', views.CategoryListView.as_view(), name='category_list'),
    path('tai-chinh/danh-muc/tao-moi/', views.CategoryCreateView.as_view(), name='category_create'),
    path('tai-chinh/danh-muc/<int:pk>/cap-nhat/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('tai-chinh/danh-muc/<int:pk>/xoa/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Transactions
    path('tai-chinh/', views.TransactionListView.as_view(), name='transactions_list'),
    path('tai-chinh/thu/tao-moi/', views.IncomeCreateView.as_view(), name='income_create'),
    path('tai-chinh/thu/xac-nhan/', views.IncomeQuickConfirmView.as_view(), name='income_quick_confirm'),
    path('tai-chinh/chi/tao-moi/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('tai-chinh/giao-dich/<int:pk>/cap-nhat/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    path('tai-chinh/giao-dich/<int:pk>/xoa/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
]
