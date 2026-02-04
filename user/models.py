from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        USER = 'USER', 'User'

    class AccountType(models.TextChoices):
        USER = 'USER', 'User'
        STORE = 'STORE', 'Store'

    uuid = models.UUIDField(primary_key=True, unique=True,
                            editable=False, null=False, default=uuid.uuid4)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )
    account_type = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.USER,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def get_google_id(self):
        return self.google_id

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4()
        super().save(*args, **kwargs)
