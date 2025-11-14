from django.db import models
from cloudinary.models import CloudinaryField
from core.utils import generate_code

from categories.models import Category
from suppliers.models import Supplier


class Product(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, blank=True, null=True, related_name="products")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, blank=True, null=True,  related_name="products")
    description = models.TextField(blank=True)
    image = CloudinaryField('image', blank=True, null=True)
    price = models.IntegerField()
    private_order = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code(Product, "SP")
        super().save(*args, **kwargs)

    def category_name(self):
        return self.category.name if self.category else None

    def supplier_name(self):
        return self.supplier.name if self.supplier else None


class Color(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="colors")
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ("product", "name")


class Size(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sizes")
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ("product", "name")
