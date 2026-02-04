from rest_framework import serializers
from .models import User
from userprofile.serializers import ProfileSerializer


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""
    full_name = serializers.SerializerMethodField()
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['uuid', 'email', 'first_name', 'last_name',
                  'full_name', 'role', 'account_type', 'profile']
        read_only_fields = ['uuid', 'email', 'role', 'account_type']

    def get_full_name(self, obj):
        return obj.get_full_name()
