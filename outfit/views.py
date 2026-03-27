import os

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api_common.pagination import Paginator

# Recommendation weights — configurable via environment variables
WEIGHT_LIKE = int(os.environ.get('RECOM_WEIGHT_LIKE', '3'))
WEIGHT_SAVE = int(os.environ.get('RECOM_WEIGHT_SAVE', '2'))
WEIGHT_TRYON = int(os.environ.get('RECOM_WEIGHT_TRYON', '2'))
WEIGHT_VIEW = int(os.environ.get('RECOM_WEIGHT_VIEW', '1'))
WEIGHT_CART = int(os.environ.get('RECOM_WEIGHT_CART', '4'))
TRENDING_DAYS = int(os.environ.get('TRENDING_DAYS', '14'))
DECAY_EXPONENT = float(os.environ.get('RECOM_DECAY_EXPONENT', '1.5'))

# Recommendation scoring weights for personalised matches
RECOM_PRODUCT_MATCH = int(os.environ.get('RECOM_PRODUCT_MATCH', '10'))
RECOM_KEYWORD_MATCH = int(os.environ.get('RECOM_KEYWORD_MATCH', '5'))
RECOM_KEYWORD_CAP = int(os.environ.get('RECOM_KEYWORD_CAP', '15'))
RECOM_STORE_MATCH = int(os.environ.get('RECOM_STORE_MATCH', '3'))
RECOM_OCCASION_MATCH = int(os.environ.get('RECOM_OCCASION_MATCH', '2'))
RECOM_PRICE_MATCH = int(os.environ.get('RECOM_PRICE_MATCH', '1'))
from cart.models import CartAddEvent
from .models import Outfit, OutfitItem, OutfitLike, OutfitSave, OutfitTryOn, OutfitView
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
        liked = self.request.query_params.get('liked')
        saved = self.request.query_params.get('saved')

        if self.request.user.is_authenticated and (liked == 'true' or saved == 'true'):
            queryset = Outfit.objects.filter(
                status=Outfit.Status.PUBLISHED,
                is_hidden=False,
            ).prefetch_related('items__product__store')

            if liked == 'true':
                queryset = queryset.filter(likes__user=self.request.user)
            if saved == 'true':
                queryset = queryset.filter(saves__user=self.request.user)
        else:
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
        detail_serializer = OutfitDetailSerializer(
            outfit,
            context={'request': request},
        )
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

        serializer = OutfitDetailSerializer(outfit, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, outfit_uuid):
        outfit = self.get_object(outfit_uuid)
        self.ensure_owner(outfit, request.user)

        serializer = OutfitMetadataUpdateSerializer(
            outfit,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        detail_serializer = OutfitDetailSerializer(
            outfit,
            context={'request': request},
        )
        return Response(detail_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, outfit_uuid):
        outfit = self.get_object(outfit_uuid)
        self.ensure_owner(outfit, request.user)
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
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = OutfitDetailSerializer(outfit, context={'request': request})
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
        detail_serializer = OutfitDetailSerializer(
            refreshed_outfit,
            context={'request': request},
        )
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
            serializer = OutfitDetailSerializer(outfit, context={'request': request})
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

        serializer = OutfitDetailSerializer(outfit, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class OutfitUnpublishView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, outfit_uuid):
        outfit = get_object_or_404(
            Outfit.objects.prefetch_related('items__product__store').select_related('owner'),
            uuid=outfit_uuid,
            owner=request.user,
        )

        if outfit.status != Outfit.Status.PUBLISHED:
            return Response(
                {'status': ['Only published outfits can be unpublished.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outfit.status = Outfit.Status.DRAFT
        outfit.save(update_fields=['status', 'updated_at'])

        serializer = OutfitDetailSerializer(outfit, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExploreOutfitListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
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
                | Q(items__product_name__icontains=search_term)
            ).distinct()

        store_filter = self.request.query_params.get('store', '').strip()
        if store_filter:
            slugs = [value.strip() for value in store_filter.split(',') if value.strip()]
            if slugs:
                queryset = queryset.filter(items__store_slug__in=slugs).distinct()

        occasion = self.request.query_params.get('occasion', '').strip()
        if occasion:
            queryset = queryset.filter(occasion=occasion)

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

        detail_serializer = OutfitDetailSerializer(
            outfit,
            context={'request': request},
        )
        return Response(detail_serializer.data, status=status.HTTP_200_OK)


class OutfitLikeView(APIView):
    """Toggle like on an outfit. POST to like, DELETE to unlike."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, outfit_uuid):
        outfit = get_object_or_404(
            Outfit, uuid=outfit_uuid, status=Outfit.Status.PUBLISHED, is_hidden=False
        )
        _, created = OutfitLike.objects.get_or_create(user=request.user, outfit=outfit)
        return Response(
            {'liked': True, 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, outfit_uuid):
        outfit = get_object_or_404(Outfit, uuid=outfit_uuid)
        OutfitLike.objects.filter(user=request.user, outfit=outfit).delete()
        return Response({'liked': False}, status=status.HTTP_200_OK)


class OutfitSaveView(APIView):
    """Toggle save on an outfit. POST to save, DELETE to unsave."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, outfit_uuid):
        outfit = get_object_or_404(
            Outfit, uuid=outfit_uuid, status=Outfit.Status.PUBLISHED, is_hidden=False
        )
        _, created = OutfitSave.objects.get_or_create(user=request.user, outfit=outfit)
        return Response(
            {'saved': True, 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, outfit_uuid):
        outfit = get_object_or_404(Outfit, uuid=outfit_uuid)
        OutfitSave.objects.filter(user=request.user, outfit=outfit).delete()
        return Response({'saved': False}, status=status.HTTP_200_OK)


class OutfitViewTrackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, outfit_uuid):
        outfit = get_object_or_404(Outfit, uuid=outfit_uuid, status=Outfit.Status.PUBLISHED, is_hidden=False)

        user = request.user if request.user.is_authenticated else None
        session_id = request.data.get('session_id', '')

        dedup_seconds = int(os.environ.get('VIEW_DEDUP_SECONDS', '3600'))
        cutoff = timezone.now() - timezone.timedelta(seconds=dedup_seconds)

        if user:
            recent = OutfitView.objects.filter(user=user, outfit=outfit, created_at__gte=cutoff).exists()
        elif session_id:
            recent = OutfitView.objects.filter(session_id=session_id, outfit=outfit, created_at__gte=cutoff).exists()
        else:
            recent = False

        if not recent:
            OutfitView.objects.create(user=user, outfit=outfit, session_id=session_id)

        return Response({'recorded': not recent}, status=status.HTTP_200_OK)


class OutfitTryOnTrackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, outfit_uuid):
        outfit = get_object_or_404(Outfit, uuid=outfit_uuid, status=Outfit.Status.PUBLISHED, is_hidden=False)
        OutfitTryOn.objects.create(user=request.user, outfit=outfit)
        return Response({'recorded': True}, status=status.HTTP_201_CREATED)


class TrendingOutfitListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()

        candidates = list(
            Outfit.objects.filter(
                status=Outfit.Status.PUBLISHED,
                is_hidden=False,
                published_at__isnull=False,
                published_at__gte=now - timezone.timedelta(days=TRENDING_DAYS),
            ).select_related('owner').prefetch_related('items', 'likes', 'saves', 'tryons', 'views', 'cart_adds')
            [:100]
        )

        scored = []
        for outfit in candidates:
            engagement = (
                outfit.likes.count() * WEIGHT_LIKE
                + outfit.saves.count() * WEIGHT_SAVE
                + outfit.tryons.count() * WEIGHT_TRYON
                + outfit.views.count() * WEIGHT_VIEW
                + outfit.cart_adds.count() * WEIGHT_CART
            )
            hours = max((now - outfit.published_at).total_seconds() / 3600, 1)
            score = engagement / (hours ** DECAY_EXPONENT)
            scored.append((score, outfit))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_outfits = [item[1] for item in scored[:10]]

        serializer = ExploreOutfitSerializer(
            top_outfits, many=True, context={'request': request}
        )
        return Response(serializer.data)


class RecommendedOutfitListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return self._fallback_trending(request)

        liked_outfit_ids = OutfitLike.objects.filter(user=request.user).values_list('outfit_id', flat=True)
        saved_outfit_ids = OutfitSave.objects.filter(user=request.user).values_list('outfit_id', flat=True)
        carted_outfit_ids = CartAddEvent.objects.filter(user=request.user).values_list('outfit_id', flat=True)
        interacted_ids = set(liked_outfit_ids) | set(saved_outfit_ids) | set(carted_outfit_ids)

        if not interacted_ids:
            return self._fallback_trending(request)

        liked_items = OutfitItem.objects.filter(outfit_id__in=interacted_ids)

        product_ids = set(liked_items.values_list('product_id', flat=True))
        store_slugs = set(liked_items.values_list('store_slug', flat=True))

        name_keywords = set()
        for name in liked_items.values_list('product_name', flat=True):
            for word in name.lower().split():
                cleaned = ''.join(c for c in word if c.isalnum())
                if len(cleaned) >= 3:
                    name_keywords.add(cleaned)

        prices = [p for p in liked_items.values_list('price', flat=True) if p is not None]
        min_price = float(min(prices)) * 0.7 if prices else 0
        max_price = float(max(prices)) * 1.3 if prices else 9999

        liked_occasions = set(
            Outfit.objects.filter(uuid__in=interacted_ids, occasion__isnull=False)
            .exclude(occasion='')
            .values_list('occasion', flat=True)
        )

        candidates = (
            Outfit.objects.filter(
                status=Outfit.Status.PUBLISHED,
                is_hidden=False,
                published_at__isnull=False,
            )
            .exclude(uuid__in=interacted_ids)
            .exclude(owner=request.user)
            .select_related('owner')
            .prefetch_related('items')
            [:100]
        )

        scored = []
        for outfit in candidates:
            score = 0
            reason = ""
            outfit_items = list(outfit.items.all())

            for item in outfit_items:
                if item.product_id in product_ids:
                    score += RECOM_PRODUCT_MATCH
                    if not reason:
                        reason = f"Features {item.product_name}"

            keyword_score = 0
            for item in outfit_items:
                item_words = {w.lower() for w in item.product_name.split() if len(w) >= 3}
                matches = item_words & name_keywords
                if matches:
                    keyword_score += len(matches) * RECOM_KEYWORD_MATCH
                    if not reason:
                        reason = "Similar to products you liked"
            score += min(keyword_score, RECOM_KEYWORD_CAP)

            for item in outfit_items:
                if item.store_slug in store_slugs:
                    score += RECOM_STORE_MATCH
                    if not reason:
                        reason = f"From {item.store_name}"

            if outfit.occasion and outfit.occasion in liked_occasions:
                score += RECOM_OCCASION_MATCH
                if not reason:
                    reason = f"Popular in {outfit.occasion}"

            for item in outfit_items:
                if item.price and min_price <= float(item.price) <= max_price:
                    score += RECOM_PRICE_MATCH
                    break

            if not reason:
                reason = "Recommended for you"

            if score > 0:
                scored.append((score, reason, outfit))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_outfits = scored[:10]

        serializer = ExploreOutfitSerializer(
            [item[2] for item in top_outfits],
            many=True,
            context={'request': request},
        )

        results = serializer.data
        for i, item in enumerate(top_outfits):
            if i < len(results):
                results[i]['recommendation_reason'] = item[1]

        return Response(results)

    def _fallback_trending(self, request):
        now = timezone.now()

        candidates = list(
            Outfit.objects.filter(
                status=Outfit.Status.PUBLISHED,
                is_hidden=False,
                published_at__isnull=False,
                published_at__gte=now - timezone.timedelta(days=TRENDING_DAYS),
            ).select_related('owner').prefetch_related('items', 'likes', 'saves', 'tryons', 'views', 'cart_adds')
            [:100]
        )

        scored = []
        for outfit in candidates:
            engagement = (
                outfit.likes.count() * WEIGHT_LIKE
                + outfit.saves.count() * WEIGHT_SAVE
                + outfit.tryons.count() * WEIGHT_TRYON
                + outfit.views.count() * WEIGHT_VIEW
                + outfit.cart_adds.count() * WEIGHT_CART
            )
            hours = max((now - outfit.published_at).total_seconds() / 3600, 1)
            score = engagement / (hours ** DECAY_EXPONENT)
            scored.append((score, outfit))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_outfits = [item[1] for item in scored[:10]]

        serializer = ExploreOutfitSerializer(top_outfits, many=True, context={'request': request})
        results = serializer.data
        for item in results:
            item['recommendation_reason'] = 'Trending now'
        return Response(results)
