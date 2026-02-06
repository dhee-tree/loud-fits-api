import json
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.filters import SearchFilter, OrderingFilter

from api_common.pagination import Paginator
from .filters import StoreProductFilter
from .permissions import IsStoreOwner
from .serializers import FeedUploadSerializer, validate_feed_products
from product.models import Product, ProductImportBatch
from product.serializers import ProductListSerializer


class StoreProductListView(generics.ListAPIView):
    """
    GET /api/store/products/

    List products for the authenticated store owner with filtering and pagination.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    serializer_class = ProductListSerializer
    pagination_class = Paginator
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StoreProductFilter
    search_fields = ["name", "external_id"]
    ordering_fields = ["created_at", "updated_at",
                       "name", "price", "stock_status", "stock_quantity"]

    def get_queryset(self):
        return Product.objects.filter(store=self.request.user.store)


class FeedPreviewView(APIView):
    """
    POST /api/store/feed/preview
    
    Validates uploaded JSON feed and returns a preview without writing to DB.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        # Handle multipart file upload or JSON body
        if 'feed' in request.FILES:
            try:
                feed_file = request.FILES['feed']
                feed_data = json.load(feed_file)
            except json.JSONDecodeError as e:
                return Response(
                    {'error': f'Invalid JSON file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif request.data and 'products' in request.data:
            feed_data = request.data
        else:
            return Response(
                {'error': 'No feed data provided. Upload a JSON file or provide a products array.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate top-level structure
        serializer = FeedUploadSerializer(data=feed_data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid feed structure', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate individual products
        products = serializer.validated_data['products']
        validation_result = validate_feed_products(products)

        # Build preview response
        is_valid = validation_result['failed_count'] == 0
        sample_products = validation_result['valid_products'][:5]

        return Response({
            'is_valid': is_valid,
            'total_products': validation_result['total'],
            'valid_count': validation_result['valid_count'],
            'failed_count': validation_result['failed_count'],
            'counts_by_category': validation_result['counts_by_category'],
            'sample_products': sample_products,
            'errors': validation_result['errors'],
        }, status=status.HTTP_200_OK)


class FeedImportView(APIView):
    """
    POST /api/store/feed/import
    
    Validates and imports products from JSON feed into the database.
    Performs upsert by (store, external_id).
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        store = request.user.store

        # Handle multipart file upload or JSON body
        if 'feed' in request.FILES:
            try:
                feed_file = request.FILES['feed']
                feed_data = json.load(feed_file)
            except json.JSONDecodeError as e:
                return Response(
                    {'error': f'Invalid JSON file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif request.data and 'products' in request.data:
            feed_data = request.data
        else:
            return Response(
                {'error': 'No feed data provided. Upload a JSON file or provide a products array.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate top-level structure
        serializer = FeedUploadSerializer(data=feed_data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid feed structure', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate individual products
        products = serializer.validated_data['products']
        validation_result = validate_feed_products(products)

        # Create import batch record
        batch = ProductImportBatch.objects.create(
            store=store,
            uploaded_by=request.user,
            total=validation_result['total'],
            failed=validation_result['failed_count'],
        )

        imported_count = 0
        updated_count = 0

        # Upsert valid products
        for product_data in validation_result['valid_products']:
            external_id = product_data['external_id']

            existing_product = Product.objects.filter(
                store=store,
                external_id=external_id
            ).first()

            if existing_product:
                # Update existing product
                for field, value in product_data.items():
                    if field != 'external_id':
                        setattr(existing_product, field, value)
                existing_product.save()
                updated_count += 1
            else:
                # Create new product
                Product.objects.create(
                    store=store,
                    **product_data
                )
                imported_count += 1

        # Update batch with results
        batch.imported = imported_count
        batch.updated = updated_count
        batch.save()

        # Update store's last upload timestamp
        store.feed_last_uploaded_at = timezone.now()
        store.save(update_fields=['feed_last_uploaded_at'])

        return Response({
            'batch_id': str(batch.uuid),
            'total': validation_result['total'],
            'imported': imported_count,
            'updated': updated_count,
            'failed': validation_result['failed_count'],
            'errors': validation_result['errors'],
        }, status=status.HTTP_201_CREATED)
