from rest_framework import serializers

from product.models import Product
from .models import Outfit, OutfitItem


class OutfitItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source='product.uuid', read_only=True)

    class Meta:
        model = OutfitItem
        fields = [
            'slot',
            'product_id',
            'product_name',
            'image_url_used',
            'product_url',
            'store_name',
            'store_slug',
            'price',
            'currency',
        ]


class OutfitDetailSerializer(serializers.ModelSerializer):
    items = OutfitItemSerializer(many=True, read_only=True)

    class Meta:
        model = Outfit
        fields = [
            'uuid',
            'status',
            'title',
            'notes',
            'created_at',
            'updated_at',
            'published_at',
            'items',
        ]


class OutfitCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outfit
        fields = ['title', 'notes']
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True},
            'notes': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        request = self.context['request']
        return Outfit.objects.create(
            owner=request.user,
            status=Outfit.Status.DRAFT,
            **validated_data,
        )


class OutfitMetadataUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outfit
        fields = ['title', 'notes']
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True},
            'notes': {'required': False, 'allow_blank': True},
        }


class OutfitSlotSetSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(required=True)

    def validate_product_id(self, value):
        try:
            product = Product.objects.select_related('store').get(
                uuid=value,
                is_active=True,
            )
        except Product.DoesNotExist as exc:
            raise serializers.ValidationError(
                'Product does not exist or is not active.'
            ) from exc

        self.context['product'] = product
        return value

    def validate(self, attrs):
        slot = self.context.get('slot')
        product = self.context['product']

        if slot and product.category != slot:
            raise serializers.ValidationError({
                'product_id': [f"Product category must match slot '{slot}'."]
            })

        attrs['product'] = product
        return attrs
