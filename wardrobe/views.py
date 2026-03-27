from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from outfit.models import Outfit, OutfitItem
from outfit.serializers import ExploreOutfitSerializer
from product.models import Product
from .models import WardrobeItem
from .serializers import WardrobeItemSerializer, AddToWardrobeSerializer


class WardrobeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = WardrobeItem.objects.filter(
            user=request.user,
        ).select_related('product__store')
        serializer = WardrobeItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = AddToWardrobeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = Product.objects.get(uuid=serializer.validated_data['product_id'])
        item, created = WardrobeItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'source': WardrobeItem.Source.MANUAL},
        )

        response_serializer = WardrobeItemSerializer(item, context={'request': request})
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class WardrobeItemDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, item_uuid):
        item = get_object_or_404(WardrobeItem, uuid=item_uuid, user=request.user)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StyledWithView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_uuid):
        outfit_ids = (
            OutfitItem.objects.filter(product_id=product_uuid)
            .values_list('outfit_id', flat=True)
        )

        outfits = (
            Outfit.objects.filter(
                uuid__in=outfit_ids,
                status=Outfit.Status.PUBLISHED,
                is_hidden=False,
                published_at__isnull=False,
            )
            .exclude(owner=request.user)
            .select_related('owner')
            .prefetch_related('items')
            [:20]
        )

        serializer = ExploreOutfitSerializer(
            outfits, many=True, context={'request': request}
        )
        return Response(serializer.data)
