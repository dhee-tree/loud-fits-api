import uuid
from pathlib import Path
from django.db import models
from django.conf import settings
from api_common.media import build_private_media_url
from store.models import Store


class CategoryChoices(models.TextChoices):
    TOP = 'top', 'Top'
    BOTTOM = 'bottom', 'Bottom'


class StockStatus(models.TextChoices):
    IN_STOCK = 'in_stock', 'In Stock'
    OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'
    LOW_STOCK = 'low_stock', 'Low Stock'


def product_image_upload_to(instance, filename):
    extension = Path(filename).suffix.lower() or '.jpg'
    unique_suffix = uuid.uuid4().hex[:8]
    return f"products/{instance.uuid}-{unique_suffix}{extension}"


class Product(models.Model):
    LOW_STOCK_THRESHOLD = 10

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products'
    )
    external_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices
    )
    image_url = models.URLField(max_length=2048)
    uploaded_image = models.ImageField(
        upload_to=product_image_upload_to,
        max_length=255,
        blank=True,
        null=True,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    product_url = models.URLField(max_length=2048)
    tryon_template_key = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    stock_status = models.CharField(
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.OUT_OF_STOCK
    )
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'external_id'],
                name='unique_store_external_id'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.store.name})"

    def calculate_stock_status(self):
        """Calculate stock status based on stock_quantity."""
        if self.stock_quantity is None or self.stock_quantity == 0:
            return StockStatus.OUT_OF_STOCK
        elif self.stock_quantity <= self.LOW_STOCK_THRESHOLD:
            return StockStatus.LOW_STOCK
        return StockStatus.IN_STOCK

    def update_stock_status(self):
        """Update stock_status based on stock_quantity and save."""
        self.stock_status = self.calculate_stock_status()
        self.save(update_fields=['stock_status', 'updated_at'])

    def get_image_url(self, request=None):
        if self.uploaded_image:
            return build_private_media_url(self.uploaded_image, request=request)
        return self.image_url


class ProductImportBatch(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='import_batches'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_imports'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    imported = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Product import batches'

    def __str__(self):
        return f"Import {self.created_at} - {self.store.name}"
