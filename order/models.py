import uuid
from django.db import models
from user.models import User
from product.models import Product
from store.models import Store


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        REFUNDED = 'refunded', 'Refunded'
        CANCELLED = 'cancelled', 'Cancelled'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='GBP')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.uuid} by {self.user.email} ({self.status})"


class OrderItem(models.Model):
    class StoreStatus(models.TextChoices):
        PENDING = 'pending'
        PROCESSING = 'processing'
        SHIPPED = 'shipped'
        COMPLETED = 'completed'
        REFUNDED = 'refunded'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    product_name = models.CharField(max_length=255)
    store_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    store_status = models.CharField(max_length=20, choices=StoreStatus.choices, default=StoreStatus.PENDING)

    class Meta:
        ordering = ['product_name']

    def __str__(self):
        return f"{self.product_name} x{self.quantity} in Order {self.order.uuid}"
