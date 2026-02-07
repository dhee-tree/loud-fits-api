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


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "uuid",
            "external_id",
            "name",
            "category",
            "image_url",
            "is_active",
            "stock_status",
            "updated_at",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
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


class ProductUpdateSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.IntegerField(
        required=False, allow_null=True, min_value=0)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Product
        fields = [
            "external_id",
            "name",
            "category",
            "image_url",
            "price",
            "currency",
            "product_url",
            "is_active",
            "stock_quantity",
        ]

    def validate_external_id(self, value):
        store = self.context.get("store")
        if not store:
            return value
        queryset = Product.objects.filter(store=store, external_id=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "External ID already exists for this store.")
        return value

    def update(self, instance, validated_data):
        stock_quantity_provided = "stock_quantity" in validated_data
        instance = super().update(instance, validated_data)
        if stock_quantity_provided:
            instance.stock_status = instance.calculate_stock_status()
            instance.save(update_fields=["stock_status", "updated_at"])
        return instance
