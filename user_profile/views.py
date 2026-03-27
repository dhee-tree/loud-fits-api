from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ProfileSerializer
from .models import CreatorFollow


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user.profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = ProfileSerializer(
            request.user.profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreatorProfileView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, username):
        from user.models import User
        from outfit.models import Outfit
        from outfit.serializers import ExploreOutfitSerializer

        user = get_object_or_404(User, username=username)
        profile = user.profile

        outfits = Outfit.objects.filter(
            owner=user,
            status=Outfit.Status.PUBLISHED,
            is_hidden=False,
        ).select_related('owner').prefetch_related('items')

        follower_count = user.followers.count()
        outfit_count = outfits.count()
        total_likes = sum(o.likes.count() for o in outfits)

        is_following = False
        if request.user.is_authenticated and request.user != user:
            is_following = CreatorFollow.objects.filter(
                follower=request.user, following=user
            ).exists()

        outfit_serializer = ExploreOutfitSerializer(
            outfits, many=True, context={'request': request}
        )

        profile_picture_url = None
        if profile.profile_picture:
            profile_picture_url = request.build_absolute_uri(profile.profile_picture.url)

        return Response({
            'username': user.username,
            'display_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'profile_picture': profile_picture_url,
            'bio': profile.bio,
            'portfolio_url': profile.portfolio_url,
            'is_hireable': profile.is_hireable,
            'follower_count': follower_count,
            'outfit_count': outfit_count,
            'total_likes': total_likes,
            'is_following': is_following,
            'is_self': request.user.is_authenticated and request.user.uuid == user.uuid,
            'outfits': outfit_serializer.data,
        })


class CreatorFollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, username):
        from user.models import User
        target = get_object_or_404(User, username=username)
        if target == request.user:
            return Response(
                {'detail': 'You cannot follow yourself.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = CreatorFollow.objects.get_or_create(
            follower=request.user, following=target
        )
        return Response(
            {'following': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, username):
        from user.models import User
        target = get_object_or_404(User, username=username)
        CreatorFollow.objects.filter(follower=request.user, following=target).delete()
        return Response({'following': False}, status=status.HTTP_200_OK)


class CreatorEnquiryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, username):
        from user.models import User
        target = get_object_or_404(User, username=username)
        if not target.profile.is_hireable:
            return Response(
                {'detail': 'This creator is not available for hire.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                {'message': ['A message is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {'detail': 'Enquiry sent successfully.'},
            status=status.HTTP_200_OK,
        )
