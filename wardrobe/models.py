import uuid
from django.db import models
from user.models import User
from product.models import Product


class WardrobeItem(models.Model):
    class Source(models.TextChoices):
        PURCHASED = 'purchased', 'Purchased'
        MANUAL = 'manual', 'Manual'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wardrobe_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wardrobe_entries')
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_wardrobe_item')
        ]
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} owns {self.product.name}"
