from rest_framework import serializers

from .models import AvatarProfile
from .registry import GARMENT_TEMPLATE_REGISTRY, TEMPLATE_DEFAULTS_BY_SLOT


class AvatarProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvatarProfile
        fields = [
            'uuid',
            'config',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class AvatarProfileUpdateSerializer(serializers.Serializer):
    config = serializers.DictField(child=serializers.CharField(), required=True)

    def validate_config(self, value):
        allowed_keys = {'body_type', 'skin_tone'}
        errors = {}

        for key in value:
            if key not in allowed_keys:
                errors[key] = ['Unsupported config key.']

        body_type = value.get('body_type')
        if body_type is not None and body_type not in AvatarProfile.ALLOWED_BODY_TYPES:
            errors['body_type'] = ['Invalid body type.']

        skin_tone = value.get('skin_tone')
        if skin_tone is not None and skin_tone not in AvatarProfile.ALLOWED_SKIN_TONES:
            errors['skin_tone'] = ['Invalid skin tone.']

        if errors:
            raise serializers.ValidationError(errors)

        return value


class AvatarTemplateAssetSerializer(serializers.Serializer):
    asset_url = serializers.CharField(allow_blank=True, allow_null=True)


class AvatarTemplateSerializer(serializers.Serializer):
    key = serializers.CharField()
    slot = serializers.ChoiceField(choices=['top', 'bottom'])
    display_name = serializers.CharField()
    assets = AvatarTemplateAssetSerializer()


class AvatarTemplateRegistrySerializer(serializers.Serializer):
    version = serializers.CharField()
    defaults = serializers.DictField(child=serializers.CharField())
    templates = AvatarTemplateSerializer(many=True)

    @staticmethod
    def build_payload():
        return {
            'version': '2026-02-18',
            'defaults': TEMPLATE_DEFAULTS_BY_SLOT,
            'templates': GARMENT_TEMPLATE_REGISTRY,
        }

