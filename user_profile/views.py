from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ProfileSerializer


class ProfileView(APIView):
    """
    API endpoint to get/update the current user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get the current user's profile."""
        serializer = ProfileSerializer(request.user.profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update the current user's profile."""
        serializer = ProfileSerializer(
            request.user.profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
