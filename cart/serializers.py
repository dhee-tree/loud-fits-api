from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source='product.uuid', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_currency = serializers.CharField(source='product.currency', read_only=True)
    image_url = serializers.SerializerMethodField()
    store_name = serializers.CharField(source='product.store.name', read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'uuid', 'product_id', 'product_name', 'product_price',
            'product_currency', 'image_url', 'store_name', 'quantity', 'added_at',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        return obj.product.get_image_url(request=request)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['uuid', 'items', 'item_count', 'subtotal', 'updated_at']

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_subtotal(self, obj):
        total = sum(
            item.product.price * item.quantity
            for item in obj.items.select_related('product').all()
        )
        return str(total)


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    outfit_uuid = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_product_id(self, value):
        from product.models import Product
        if not Product.objects.filter(uuid=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or not available.")
        return value

    def validate_outfit_uuid(self, value):
        if value is None:
            return value
        from outfit.models import Outfit
        if not Outfit.objects.filter(uuid=value, status=Outfit.Status.PUBLISHED, is_hidden=False).exists():
            raise serializers.ValidationError("Outfit not found or not available.")
        return value
