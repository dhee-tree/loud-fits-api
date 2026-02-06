from rest_framework import serializers
from .models import Product


class StoreSummarySerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class ProductListSerializer(serializers.ModelSerializer):
    store = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "uuid",
            "external_id",
            "name",
            "category",
            "image_url",
            "price",
            "currency",
            "product_url",
            "is_active",
            "stock_status",
            "stock_quantity",
            "created_at",
            "updated_at",
            "store",
        ]

    def get_store(self, obj):
        return {
            "uuid": obj.store.uuid,
            "name": obj.store.name,
            "slug": obj.store.slug,
        }
