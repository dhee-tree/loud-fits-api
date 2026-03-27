import re
from rest_framework import serializers
from .models import User
from user_profile.serializers import ProfileSerializer


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['uuid', 'email', 'username', 'first_name', 'last_name',
                  'full_name', 'role', 'account_type', 'profile']
        read_only_fields = ['uuid', 'email', 'role', 'account_type']

    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', value):
            raise serializers.ValidationError(
                "Username must be 3-20 characters, alphanumeric and underscores only."
            )
        if User.objects.filter(username=value).exclude(uuid=self.instance.uuid).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def get_full_name(self, obj):
        return obj.get_full_name()
