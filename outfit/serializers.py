from rest_framework import serializers

from product.models import Product
from .models import Outfit, OutfitItem


def get_creator_display_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    if full_name:
        return full_name
    if user.username:
        return user.username
    if user.email:
        return user.email.split('@')[0]
    return 'User'


class OutfitCreatorSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    username = serializers.CharField()
    display_name = serializers.CharField()


class OutfitItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source='product.uuid', read_only=True)
    image_url_used = serializers.SerializerMethodField()
    tryon_asset_url = serializers.SerializerMethodField()

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
            'tryon_asset_url',
        ]

    def get_tryon_asset_url(self, obj):
        request = self.context.get('request')
        return obj.product.get_tryon_asset_url(request=request)

    def get_image_url_used(self, obj):
        request = self.context.get('request')
        if hasattr(obj.product, 'get_image_url'):
            current_image_url = obj.product.get_image_url(request=request)
            if current_image_url:
                return current_image_url
        return obj.image_url_used


class OutfitDetailSerializer(serializers.ModelSerializer):
    items = OutfitItemSerializer(many=True, read_only=True)
    creator = serializers.SerializerMethodField()

    class Meta:
        model = Outfit
        fields = [
            'uuid',
            'creator',
            'status',
            'title',
            'notes',
            'created_at',
            'updated_at',
            'published_at',
            'is_hidden',
            'hidden_reason',
            'items',
        ]

    def get_creator(self, obj):
        return {
            'uuid': obj.owner.uuid,
            'username': obj.owner.username,
            'display_name': get_creator_display_name(obj.owner),
        }


class ExploreOutfitSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()
    top_image_url = serializers.SerializerMethodField()
    bottom_image_url = serializers.SerializerMethodField()
    shoes_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Outfit
        fields = [
            'uuid',
            'title',
            'published_at',
            'creator',
            'top_image_url',
            'bottom_image_url',
            'shoes_image_url',
        ]

    def get_creator(self, obj):
        return {
            'uuid': obj.owner.uuid,
            'username': obj.owner.username,
            'display_name': get_creator_display_name(obj.owner),
        }

    @staticmethod
    def get_slot_image(obj, slot, request=None):
        for item in obj.items.all():
            if item.slot == slot:
                if hasattr(item.product, 'get_image_url'):
                    current_image_url = item.product.get_image_url(request=request)
                    if current_image_url:
                        return current_image_url
                return item.image_url_used
        return None

    def get_top_image_url(self, obj):
        request = self.context.get('request')
        return self.get_slot_image(obj, OutfitItem.Slot.TOP, request=request)

    def get_bottom_image_url(self, obj):
        request = self.context.get('request')
        return self.get_slot_image(obj, OutfitItem.Slot.BOTTOM, request=request)

    def get_shoes_image_url(self, obj):
        request = self.context.get('request')
        return self.get_slot_image(obj, OutfitItem.Slot.SHOES, request=request)


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


class OutfitModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outfit
        fields = ['is_hidden', 'hidden_reason']
        extra_kwargs = {
            'is_hidden': {'required': True},
            'hidden_reason': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, attrs):
        is_hidden = attrs.get('is_hidden', getattr(self.instance, 'is_hidden', False))
        hidden_reason = attrs.get('hidden_reason', getattr(self.instance, 'hidden_reason', None))

        if not is_hidden:
            attrs['hidden_reason'] = None
            return attrs

        if hidden_reason is None:
            return attrs

        if isinstance(hidden_reason, str):
            cleaned = hidden_reason.strip()
            attrs['hidden_reason'] = cleaned or None
        return attrs
