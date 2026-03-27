from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemStatusHistoryReadSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    changed_by = serializers.UUIDField(read_only=True, source='changed_by_id')
    note = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class OrderItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    status_history = OrderItemStatusHistoryReadSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'uuid', 'product_name', 'store_name', 'quantity',
            'price_at_purchase', 'currency', 'image_url',
            'store_status', 'status_history',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if hasattr(obj.product, 'get_image_url'):
            return obj.product.get_image_url(request=request)
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['uuid', 'status', 'total', 'currency', 'items', 'created_at', 'updated_at']
