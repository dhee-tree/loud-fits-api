from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AvatarProfile
from .serializers import (
    AvatarProfileSerializer,
    AvatarProfileUpdateSerializer,
    AvatarTemplateRegistrySerializer,
)


class AvatarMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_profile(self, request):
        profile, _ = AvatarProfile.objects.get_or_create(
            user=request.user,
            defaults={'config': AvatarProfile.default_config()},
        )
        profile.config = AvatarProfile.normalise_config(profile.config)
        profile.save(update_fields=['config', 'updated_at'])
        return profile

    def get(self, request):
        profile = self.get_profile(request)
        serializer = AvatarProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = self.get_profile(request)
        serializer = AvatarProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        merged_config = {
            **AvatarProfile.normalise_config(profile.config),
            **serializer.validated_data['config'],
        }
        profile.config = merged_config
        profile.save(update_fields=['config', 'updated_at'])

        response_serializer = AvatarProfileSerializer(profile)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AvatarTemplateListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payload = AvatarTemplateRegistrySerializer.build_payload()
        serializer = AvatarTemplateRegistrySerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
