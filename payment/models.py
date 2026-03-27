import uuid
from django.db import models
from django.conf import settings
from store.models import Store
from order.models import OrderItem


class PayoutMethod(models.Model):
    class MethodType(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer'
        PAYPAL = 'paypal'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='payout_methods')
    method_type = models.CharField(max_length=20, choices=MethodType.choices)
    label = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=255, blank=True, default='')
    account_holder_name = models.CharField(max_length=255)
    sort_code = models.CharField(max_length=10, blank=True, default='')
    account_number = models.CharField(max_length=20, blank=True, default='')
    iban = models.CharField(max_length=34, blank=True, default='')
    paypal_email = models.EmailField(blank=True, default='')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated_at']

    def __str__(self):
        return f"{self.label} ({self.method_type}) - {self.store.name}"


class StoreBalance(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='balance')
    currency = models.CharField(max_length=3, default='GBP')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Balance for {self.store.name}"


class Withdrawal(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        PROCESSING = 'processing'
        COMPLETED = 'completed'
        REJECTED = 'rejected'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='withdrawals')
    payout_method = models.ForeignKey(PayoutMethod, on_delete=models.SET_NULL, null=True, related_name='withdrawals')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=255, default='Loud Fits Withdrawal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Withdrawal {self.uuid} - {self.amount} {self.store.name}"


class OrderItemStatusHistory(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=OrderItem.StoreStatus.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_item.product_name} -> {self.status}"
