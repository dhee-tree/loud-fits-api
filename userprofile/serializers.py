from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for the Profile model."""

    class Meta:
        model = Profile
        fields = ['uuid', 'gender', 'avatar_size',
                  'profile_picture', 'stylist_enabled']
        read_only_fields = ['uuid']
