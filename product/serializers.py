from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from api_common.media import build_private_media_url
from .models import Product

ALLOWED_PRODUCT_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_PRODUCT_IMAGE_FORMATS = {"JPEG", "PNG"}
ALLOWED_PRODUCT_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def validate_product_image_file(file_obj):
    content_type = getattr(file_obj, "content_type", "")
    if content_type and content_type.lower() not in ALLOWED_PRODUCT_IMAGE_CONTENT_TYPES:
        raise serializers.ValidationError("Only JPG and PNG images are supported.")

    try:
        image = Image.open(file_obj)
        image.verify()
        image_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError):
        raise serializers.ValidationError("Invalid image file.")
    finally:
        file_obj.seek(0)

    if image_format not in ALLOWED_PRODUCT_IMAGE_FORMATS:
        raise serializers.ValidationError("Only JPG and PNG images are supported.")

    return file_obj


class StoreSummarySerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Compact product list for store-owner dashboard tables.
    """
    image_url = serializers.SerializerMethodField()
    has_uploaded_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "uuid",
            "external_id",
            "name",
            "category",
            "image_url",
            "has_uploaded_image",
            "is_active",
            "stock_status",
            "updated_at",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        return obj.get_image_url(request=request)

    def get_has_uploaded_image(self, obj):
        return bool(obj.uploaded_image)


class ProductBrowseSerializer(serializers.ModelSerializer):
    """
    Public browse serializer used by GET /api/products/.
    Includes store summary for client rendering.
    """
    store = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

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
            "tryon_template_key",
            "is_active",
            "stock_status",
            "updated_at",
            "store",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        return obj.get_image_url(request=request)

    def get_store(self, obj):
        return {
            "uuid": obj.store.uuid,
            "name": obj.store.name,
            "slug": obj.store.slug,
        }


class ProductDetailSerializer(serializers.ModelSerializer):
    store = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    uploaded_image_url = serializers.SerializerMethodField()
    has_uploaded_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "uuid",
            "external_id",
            "name",
            "category",
            "image_url",
            "uploaded_image_url",
            "has_uploaded_image",
            "price",
            "currency",
            "product_url",
            "tryon_template_key",
            "is_active",
            "stock_status",
            "stock_quantity",
            "created_at",
            "updated_at",
            "store",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        return obj.get_image_url(request=request)

    def get_uploaded_image_url(self, obj):
        request = self.context.get("request")
        return build_private_media_url(obj.uploaded_image, request=request)

    def get_has_uploaded_image(self, obj):
        return bool(obj.uploaded_image)

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
    uploaded_image = serializers.ImageField(required=False, allow_null=True)
    remove_uploaded_image = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Product
        fields = [
            "external_id",
            "name",
            "category",
            "image_url",
            "uploaded_image",
            "remove_uploaded_image",
            "price",
            "currency",
            "product_url",
            "tryon_template_key",
            "is_active",
            "stock_quantity",
        ]

    def validate_uploaded_image(self, value):
        if value is None:
            return value
        return validate_product_image_file(value)

    def validate(self, attrs):
        if attrs.get("remove_uploaded_image") and attrs.get("uploaded_image"):
            raise serializers.ValidationError(
                {
                    "remove_uploaded_image": [
                        "Remove uploaded image cannot be combined with a new uploaded image."
                    ]
                }
            )
        return attrs

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
        uploaded_image = validated_data.pop("uploaded_image", serializers.empty)
        remove_uploaded_image = validated_data.pop("remove_uploaded_image", False)
        previous_image_name = instance.uploaded_image.name if instance.uploaded_image else None

        instance = super().update(instance, validated_data)

        if uploaded_image is not serializers.empty:
            instance.uploaded_image = uploaded_image
            instance.save(update_fields=["uploaded_image", "updated_at"])
            if previous_image_name and previous_image_name != instance.uploaded_image.name:
                instance.uploaded_image.storage.delete(previous_image_name)
            previous_image_name = instance.uploaded_image.name

        if remove_uploaded_image and instance.uploaded_image:
            instance.uploaded_image.delete(save=False)
            instance.uploaded_image = None
            instance.save(update_fields=["uploaded_image", "updated_at"])

        if stock_quantity_provided:
            instance.stock_status = instance.calculate_stock_status()
            instance.save(update_fields=["stock_status", "updated_at"])
        return instance
