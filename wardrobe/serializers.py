from rest_framework import serializers
from product.serializers import ProductBrowseSerializer
from .models import WardrobeItem


class WardrobeItemSerializer(serializers.ModelSerializer):
    product = ProductBrowseSerializer(read_only=True)

    class Meta:
        model = WardrobeItem
        fields = ['uuid', 'product', 'source', 'added_at']


class AddToWardrobeSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

    def validate_product_id(self, value):
        from product.models import Product
        if not Product.objects.filter(uuid=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or not available.")
        return value
