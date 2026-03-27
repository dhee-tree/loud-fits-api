from rest_framework import serializers
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'uuid', 'label', 'address_line_1', 'address_line_2',
            'city', 'postcode', 'country', 'is_default',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'is_default', 'created_at', 'updated_at']
