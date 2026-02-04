from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['uuid', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['uuid', 'email']

    def get_full_name(self, obj):
        return obj.get_full_name()
