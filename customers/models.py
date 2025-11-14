from django.db import models
from cloudinary.models import CloudinaryField
from core.utils import generate_code


class Customer(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    social_link = models.URLField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    is_affiliate = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code(Customer, "KH")
        super().save(*args, **kwargs)


class QRCode(models.Model):
    name = models.CharField(max_length=255, blank=True)
    file = CloudinaryField('image', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or (self.file.name if self.file else 'QR Code')

    @property
    def url(self):
        try:
            return self.file.url
        except Exception:
            return ''
