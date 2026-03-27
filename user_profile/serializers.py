from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for the Profile model."""

    class Meta:
        model = Profile
        fields = ['uuid', 'shopping_preference', 'avatar_size',
                  'profile_picture', 'bio', 'portfolio_url', 'is_hireable',
                  'stylist_enabled', 'onboarding_completed']
        read_only_fields = ['uuid']
