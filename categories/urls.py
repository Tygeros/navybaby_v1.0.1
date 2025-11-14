from django.urls import path
from .views import (
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryDeleteView,
)

app_name = 'categories'

urlpatterns = [
    path('danh-muc', CategoryListView.as_view(), name='category_list'),
    path('danh-muc/tao-moi', CategoryCreateView.as_view(), name='category_create'),
    path('danh-muc/<slug:code>/cap-nhat', CategoryUpdateView.as_view(), name='category_update'),
    path('danh-muc/<slug:code>/xoa', CategoryDeleteView.as_view(), name='category_delete'),
]
