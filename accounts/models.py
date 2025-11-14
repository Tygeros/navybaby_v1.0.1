from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class AccountType(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
        VIEWER = "viewer", "Viewer"

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.STAFF,
    )
    is_approved = models.BooleanField(default=False, help_text="Chỉ khi được admin chấp thuận mới có thể đăng nhập.")

    def __str__(self):
        return f"{self.username} ({self.get_account_type_display()})"

    @property
    def can_edit(self):
        """Staff và Admin có thể chỉnh sửa, Viewer thì không."""
        return self.account_type in [self.AccountType.ADMIN, self.AccountType.STAFF]
