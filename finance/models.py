from django.db import models

from customers.models import Customer


class FinanceCategory(models.Model):
    TYPE_CHOICES = [
        ("INCOME", "Khoản thu"),
        ("EXPENSE", "Khoản chi"),
    ]
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class FinanceTransaction(models.Model):
    category = models.ForeignKey(FinanceCategory, on_delete=models.SET_NULL, null=True, related_name='transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)