from django.db import models

from customers.models import Customer
from products.models import Product, Color, Size 
from core.utils import generate_code


class Order(models.Model):
    STATUS_CHOICES = [
        ("created", "Đã tạo đơn hàng"),
        ("cart", "Đã thêm vào giỏ hàng"),
        ("purchased", "Đã mua hàng"),
        ("in_stock", "Hàng đã về kho"),
        ("reported", "Đã báo đơn"),
        ("reconciled", "Đã đối soát"),
        ("cancelled", "Hủy đơn"),
    ]

    code = models.CharField(max_length=20)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="orders")
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="orders", blank=True, null=True)
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name="orders", blank=True, null=True)
    amount = models.IntegerField(default=1)
    
    # Giá bán tại thời điểm tạo đơn; mặc định = giá sản phẩm, cho phép chỉnh theo từng đơn
    sale_price = models.IntegerField(blank=True, null=True)
    discount = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer} - {self.product}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code(Order, "ĐH")
        # Default sale_price from product if not specified
        if self.sale_price is None and self.product_id:
            try:
                # Use in-memory relation if already loaded, else fetch only price
                price = self.product.price if hasattr(self, 'product') and self.product else Product.objects.only('price').get(id=self.product_id).price
                self.sale_price = int(price)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def get_status_class(self):
        mapping = {
            "created": "bg-gray-900/40 border border-gray-800 text-gray-300",
            "cart": "bg-amber-900/30 border border-amber-800 text-amber-300",
            "purchased": "bg-blue-900/30 border border-blue-800 text-blue-300",
            "in_stock": "bg-indigo-900/30 border border-indigo-800 text-indigo-300",
            "reported": "bg-purple-900/30 border border-purple-800 text-purple-300",
            "reconciled": "bg-green-900/30 border border-green-800 text-green-300",
            "cancelled": "bg-red-900/30 border border-red-800 text-red-300",
        }
        return mapping.get(self.status, "bg-gray-900/40 border border-gray-800 text-gray-300")
