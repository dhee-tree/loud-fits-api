from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api_common.pagination import Paginator
from .models import Outfit, OutfitItem
from .serializers import (
    ExploreOutfitSerializer,
    OutfitCreateSerializer,
    OutfitDetailSerializer,
    OutfitMetadataUpdateSerializer,
    OutfitModerationSerializer,
    OutfitSlotSetSerializer,
)


def is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, 'is_staff', False)
            or getattr(user, 'is_superuser', False)
            or getattr(user, 'role', '') == 'Admin'
        )
    )


class OutfitListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = Paginator

    def get_queryset(self):
        queryset = Outfit.objects.filter(owner=self.request.user).prefetch_related(
            'items__product__store'
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            valid_statuses = {choice[0] for choice in Outfit.Status.choices}
            if status_filter not in valid_statuses:
                raise ValidationError({'status': ['Invalid status value.']})
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OutfitCreateSerializer
        return OutfitDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outfit = serializer.save()
        detail_serializer = OutfitDetailSerializer(outfit)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class OutfitDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, outfit_uuid):
        return get_object_or_404(
            Outfit.objects.prefetch_related('items__product__store').select_related('owner'),
            uuid=outfit_uuid,
        )

    @staticmethod
    def ensure_owner(outfit, user):
        if outfit.owner_id != user.uuid:
            raise PermissionDenied('You do not have permission to access this outfit.')

    def get(self, request, outfit_uuid):
        outfit = self.get_object(outfit_uuid)
        is_owner = request.user.is_authenticated and outfit.owner_id == request.user.uuid

        if outfit.status == Outfit.Status.DRAFT:
            if not request.user.is_authenticated:
                raise PermissionDenied('Authentication is required for draft outfits.')
            self.ensure_owner(outfit, request.user)

        if outfit.status == Outfit.Status.PUBLISHED and outfit.is_hidden:
            if not (is_owner or is_admin_user(request.user)):
                raise Http404('Outfit not available.')

        serializer = OutfitDetailSerializer(outfit)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, outfit_uuid):
        outfit = self.get_object(outfit_uuid)
        self.ensure_owner(outfit, request.user)

        if outfit.status != Outfit.Status.DRAFT:
            return Response(
                {'status': ['Only draft outfits can be updated.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OutfitMetadataUpdateSerializer(
            outfit,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        detail_serializer = OutfitDetailSerializer(outfit)
        return Response(detail_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, outfit_uuid):
        outfit = self.get_object(outfit_uuid)
        self.ensure_owner(outfit, request.user)

        if outfit.status != Outfit.Status.DRAFT:
            return Response(
                {'status': ['Only draft outfits can be deleted.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outfit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentDraftView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Outfit.objects.filter(
            owner=request.user,
            status=Outfit.Status.DRAFT,
        ).prefetch_related('items__product__store')
        outfit = queryset.order_by('-updated_at').first()

        if not outfit:
            outfit = Outfit.objects.create(owner=request.user, status=Outfit.Status.DRAFT)

        serializer = OutfitDetailSerializer(outfit)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OutfitSlotItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def validate_slot(slot):
        valid_slots = {choice[0] for choice in OutfitItem.Slot.choices}
        if slot not in valid_slots:
            raise ValidationError({'slot': ['Invalid slot value.']})

    def get_outfit(self, request, outfit_uuid):
        outfit = get_object_or_404(
            Outfit.objects.prefetch_related('items__product__store'),
            uuid=outfit_uuid,
            owner=request.user,
        )
        if outfit.status != Outfit.Status.DRAFT:
            raise ValidationError({'status': ['Only draft outfits can be modified.']})
        return outfit

    def put(self, request, outfit_uuid, slot):
        self.validate_slot(slot)
        outfit = self.get_outfit(request, outfit_uuid)

        serializer = OutfitSlotSetSerializer(data=request.data, context={'slot': slot})
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data['product']

        item, _ = OutfitItem.objects.get_or_create(
            outfit=outfit,
            slot=slot,
            defaults={
                'product': product,
                'product_name': product.name,
                'image_url_used': OutfitItem.resolve_image_url(product, request=request),
            },
        )
        item.apply_product_snapshot(product, request=request)
        item.save()
        outfit.save(update_fields=['updated_at'])

        refreshed_outfit = Outfit.objects.prefetch_related('items__product__store').get(
            uuid=outfit.uuid
        )
        detail_serializer = OutfitDetailSerializer(refreshed_outfit)
        return Response(detail_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, outfit_uuid, slot):
        self.validate_slot(slot)
        outfit = self.get_outfit(request, outfit_uuid)

        OutfitItem.objects.filter(outfit=outfit, slot=slot).delete()
        outfit.save(update_fields=['updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class OutfitPublishView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, outfit_uuid):
        outfit = get_object_or_404(
            Outfit.objects.prefetch_related('items__product__store').select_related('owner'),
            uuid=outfit_uuid,
            owner=request.user,
        )

        if outfit.status == Outfit.Status.PUBLISHED:
            if not outfit.published_at:
                outfit.published_at = timezone.now()
                outfit.save(update_fields=['published_at', 'updated_at'])
            serializer = OutfitDetailSerializer(outfit)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = outfit.items.all()
        if not items.exists():
            return Response(
                {'items': ['Add at least one item before publishing.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_slots = {OutfitItem.Slot.TOP, OutfitItem.Slot.BOTTOM}
        existing_slots = set(items.values_list('slot', flat=True))
        missing_slots = sorted(required_slots - existing_slots)
        if missing_slots:
            return Response(
                {'slots': [f"Missing required slots: {', '.join(missing_slots)}."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outfit.status = Outfit.Status.PUBLISHED
        outfit.published_at = timezone.now()
        outfit.save(update_fields=['status', 'published_at', 'updated_at'])

        serializer = OutfitDetailSerializer(outfit)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExploreOutfitListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExploreOutfitSerializer
    pagination_class = Paginator

    def get_queryset(self):
        queryset = Outfit.objects.filter(
            status=Outfit.Status.PUBLISHED,
            is_hidden=False,
            published_at__isnull=False,
        ).select_related('owner').prefetch_related('items')

        search_term = self.request.query_params.get('search', '').strip()
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term)
                | Q(owner__first_name__icontains=search_term)
                | Q(owner__last_name__icontains=search_term)
                | Q(owner__username__icontains=search_term)
                | Q(owner__email__icontains=search_term)
            )

        store_filter = self.request.query_params.get('store', '').strip()
        if store_filter:
            slugs = [value.strip() for value in store_filter.split(',') if value.strip()]
            if slugs:
                queryset = queryset.filter(items__store_slug__in=slugs).distinct()

        return queryset.order_by('-published_at', '-updated_at')


class OutfitModerationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, outfit_uuid):
        if not is_admin_user(request.user):
            raise PermissionDenied('You do not have permission to moderate outfits.')

        outfit = get_object_or_404(
            Outfit.objects.select_related('owner').prefetch_related('items__product__store'),
            uuid=outfit_uuid,
        )
        serializer = OutfitModerationSerializer(outfit, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        detail_serializer = OutfitDetailSerializer(outfit)
        return Response(detail_serializer.data, status=status.HTTP_200_OK)
