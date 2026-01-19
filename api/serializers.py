from rest_framework import serializers

class GoogleLoginSerializer(serializers.Serializer):
    """
    Serializer for validating the Google ID token sent from the frontend.
    """
    id_token = serializers.CharField(required=True, write_only=True)
