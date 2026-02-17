import uuid

from django.conf import settings
from django.db import models
from product.models import Product


class Outfit(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='outfits',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    title = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Outfit {self.uuid} ({self.status})"


class OutfitItem(models.Model):
    class Slot(models.TextChoices):
        TOP = 'top', 'Top'
        BOTTOM = 'bottom', 'Bottom'

    uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)
    outfit = models.ForeignKey(
        Outfit,
        on_delete=models.CASCADE,
        related_name='items',
    )
    slot = models.CharField(
        max_length=20,
        choices=Slot.choices,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='outfit_items',
    )
    product_name = models.CharField(max_length=255)
    image_url_used = models.URLField(max_length=2048)
    product_url = models.URLField(max_length=2048, blank=True, default='')
    store_name = models.CharField(max_length=255, blank=True, default='')
    store_slug = models.CharField(max_length=255, blank=True, default='')
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slot']
        constraints = [
            models.UniqueConstraint(
                fields=['outfit', 'slot'],
                name='unique_outfit_slot',
            ),
        ]

    def __str__(self):
        return f"{self.outfit.uuid} - {self.slot}"

    @staticmethod
    def resolve_image_url(product):
        candidate_fields = [
            'thumb_url',
            'cached_image_url',
            'source_image_url',
            'image_url_thumb',
            'image_url_cached',
            'image_url_source',
            'image_url',
        ]
        for field in candidate_fields:
            value = getattr(product, field, None)
            if value:
                return value
        return ''

    def apply_product_snapshot(self, product):
        self.product = product
        self.product_name = product.name
        self.image_url_used = self.resolve_image_url(product)
        self.product_url = getattr(product, 'product_url', '') or ''

        store = getattr(product, 'store', None)
        self.store_name = getattr(store, 'name', '') or ''
        store_slug = getattr(store, 'slug', None)
        if store_slug:
            self.store_slug = store_slug
        else:
            store_uuid = getattr(store, 'uuid', None)
            self.store_slug = str(store_uuid) if store_uuid else ''

        self.price = getattr(product, 'price', None)
        self.currency = getattr(product, 'currency', '') or ''
