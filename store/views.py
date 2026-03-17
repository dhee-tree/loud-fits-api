import json
import zipfile
from pathlib import Path
from django.utils import timezone
from django.core.files.base import ContentFile
from botocore.exceptions import BotoCoreError, ClientError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from rest_framework.filters import SearchFilter, OrderingFilter

from api_common.pagination import Paginator
from .filters import StoreProductFilter
from .permissions import IsStoreOwner
from .serializers import (
    FeedUploadSerializer,
    validate_feed_products,
    StoreManageSerializer,
    StoreLastImportSerializer,
)
from product.models import Product, ProductImportBatch
from product.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductUpdateSerializer,
    ALLOWED_PRODUCT_IMAGE_EXTENSIONS,
    ALLOWED_TRYON_ASSET_EXTENSIONS,
    validate_product_image_file,
    validate_tryon_asset_file,
)
from user.models import User


def get_validated_zip_archive(request, file_field_name):
    archive_file = request.FILES.get(file_field_name)
    if archive_file is None:
        return None, Response(
            {file_field_name: ["A ZIP file is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not zipfile.is_zipfile(archive_file):
        return None, Response(
            {file_field_name: ["Only ZIP archives are supported."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    archive_file.seek(0)
    return archive_file, None


def parse_product_asset_archive(
    archive_file,
    store,
    allowed_extensions,
    validate_file,
    invalid_extension_message,
):
    matched_files = []
    upload_candidates = []
    invalid_files = []
    missing_products = []
    seen_external_ids = set()

    archive_file.seek(0)
    with zipfile.ZipFile(archive_file) as archive:
        file_infos = [info for info in archive.infolist() if not info.is_dir()]

        for info in file_infos:
            file_name = Path(info.filename).name
            external_id = Path(file_name).stem.strip()
            extension = Path(file_name).suffix.lower()

            if extension not in allowed_extensions:
                invalid_files.append(
                    {
                        "filename": file_name,
                        "error": invalid_extension_message,
                    }
                )
                continue

            if not external_id:
                invalid_files.append(
                    {
                        "filename": file_name,
                        "error": "Filename must include a product external ID.",
                    }
                )
                continue

            if external_id in seen_external_ids:
                invalid_files.append(
                    {
                        "filename": file_name,
                        "error": "Duplicate external ID in ZIP archive.",
                    }
                )
                continue

            seen_external_ids.add(external_id)

            product = Product.objects.filter(
                store=store,
                external_id=external_id,
            ).first()
            if product is None:
                missing_products.append(external_id)
                continue

            try:
                uploaded_file = ContentFile(
                    archive.read(info),
                    name=file_name,
                )
                validate_file(uploaded_file)
            except serializers.ValidationError as exc:
                error_message = (
                    exc.detail[0]
                    if hasattr(exc, "detail") and exc.detail
                    else "Invalid image file."
                )
                invalid_files.append(
                    {
                        "filename": file_name,
                        "error": str(error_message),
                    }
                )
                continue

            matched_files.append(
                {
                    "filename": file_name,
                    "external_id": external_id,
                    "product_uuid": str(product.uuid),
                    "product_name": product.name,
                }
            )
            upload_candidates.append(
                {
                    "file_name": file_name,
                    "product": product,
                    "uploaded_file": uploaded_file,
                }
            )

    return {
        "total_files": len(file_infos),
        "matched_count": len(matched_files),
        "matched_files": matched_files,
        "missing_products": missing_products,
        "invalid_files": invalid_files,
        "can_upload": bool(upload_candidates),
        "upload_candidates": upload_candidates,
    }


def apply_product_asset_archive(upload_candidates, field_name):
    updated = 0
    for item in upload_candidates:
        product = item["product"]
        uploaded_file = item["uploaded_file"]
        file_name = item["file_name"]

        file_field = getattr(product, field_name)
        previous_file_name = file_field.name if file_field else None
        file_field.save(file_name, uploaded_file, save=False)
        product.save(update_fields=[field_name, "updated_at"])
        saved_file = getattr(product, field_name)
        if previous_file_name and previous_file_name != saved_file.name:
            saved_file.storage.delete(previous_file_name)

        updated += 1

    return updated


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


class StoreProductDetailView(APIView):
    """
    GET /api/store/products/<uuid>/
    PATCH /api/store/products/<uuid>/
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, request, product_uuid):
        return Product.objects.get(
            uuid=product_uuid,
            store=request.user.store,
        )

    def get(self, request, product_uuid):
        try:
            product = self.get_object(request, product_uuid)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductDetailSerializer(
            product,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, product_uuid):
        try:
            product = self.get_object(request, product_uuid)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductUpdateSerializer(
            product,
            data=request.data,
            partial=True,
            context={"store": request.user.store},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.save()
        response_serializer = ProductDetailSerializer(
            product,
            context={"request": request},
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class StoreProductImageBatchUploadView(APIView):
    """
    POST /api/store/products/images/upload/

    Accepts a ZIP file containing JPG or PNG files named after product external IDs.
    Example: EXT-001.jpg maps to product external_id=EXT-001.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archive_file, error_response = get_validated_zip_archive(request, "images")
        if error_response is not None:
            return error_response

        archive_result = parse_product_asset_archive(
            archive_file,
            request.user.store,
            ALLOWED_PRODUCT_IMAGE_EXTENSIONS,
            validate_product_image_file,
            "Only JPG and PNG files are supported.",
        )
        updated = apply_product_asset_archive(
            archive_result["upload_candidates"],
            "uploaded_image",
        )

        response_payload = {
            key: value
            for key, value in archive_result.items()
            if key != "upload_candidates"
        }
        response_payload["updated"] = updated

        return Response(
            response_payload,
            status=status.HTTP_200_OK,
        )


class StoreProductImageBatchPreviewView(APIView):
    """
    POST /api/store/products/images/preview/

    Validates a ZIP file containing JPG or PNG files named after product external IDs.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archive_file, error_response = get_validated_zip_archive(request, "images")
        if error_response is not None:
            return error_response

        archive_result = parse_product_asset_archive(
            archive_file,
            request.user.store,
            ALLOWED_PRODUCT_IMAGE_EXTENSIONS,
            validate_product_image_file,
            "Only JPG and PNG files are supported.",
        )
        response_payload = {
            key: value
            for key, value in archive_result.items()
            if key != "upload_candidates"
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class StoreProductThreeDAssetBatchPreviewView(APIView):
    """
    POST /api/store/products/3d-assets/preview/

    Validates a ZIP file containing GLB files named after product external IDs.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archive_file, error_response = get_validated_zip_archive(
            request,
            "assets",
        )
        if error_response is not None:
            return error_response

        archive_result = parse_product_asset_archive(
            archive_file,
            request.user.store,
            ALLOWED_TRYON_ASSET_EXTENSIONS,
            validate_tryon_asset_file,
            "Only GLB files are supported.",
        )
        response_payload = {
            key: value
            for key, value in archive_result.items()
            if key != "upload_candidates"
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class StoreProductThreeDAssetBatchUploadView(APIView):
    """
    POST /api/store/products/3d-assets/upload/

    Accepts a ZIP file containing GLB files named after product external IDs.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archive_file, error_response = get_validated_zip_archive(
            request,
            "assets",
        )
        if error_response is not None:
            return error_response

        archive_result = parse_product_asset_archive(
            archive_file,
            request.user.store,
            ALLOWED_TRYON_ASSET_EXTENSIONS,
            validate_tryon_asset_file,
            "Only GLB files are supported.",
        )
        updated = apply_product_asset_archive(
            archive_result["upload_candidates"],
            "tryon_asset",
        )

        response_payload = {
            key: value
            for key, value in archive_result.items()
            if key != "upload_candidates"
        }
        response_payload["updated"] = updated

        return Response(response_payload, status=status.HTTP_200_OK)


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
        is_valid = validation_result['valid_count'] > 0
        sample_products = validation_result['valid_products'][:5]
        missing_stock_quantity_count = validation_result.get(
            'missing_stock_quantity_count',
            0,
        )
        missing_stock_quantity_message = (
            f"{missing_stock_quantity_count} product(s) are missing stock quantity. "
            "These will default to out of stock."
            if missing_stock_quantity_count > 0
            else None
        )

        return Response({
            'is_valid': is_valid,
            'total_products': validation_result['total'],
            'valid_count': validation_result['valid_count'],
            'failed_count': validation_result['failed_count'],
            'counts_by_category': validation_result['counts_by_category'],
            'missing_stock_quantity_count': missing_stock_quantity_count,
            'missing_stock_quantity_message': missing_stock_quantity_message,
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

        if validation_result['valid_count'] == 0:
            return Response({
                'error': 'No valid products to import.',
                'failed_count': validation_result['failed_count'],
                'errors': validation_result['errors'],
            }, status=status.HTTP_400_BAD_REQUEST)

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
            stock_quantity = product_data.get('stock_quantity')
            product_data['stock_status'] = Product(
                stock_quantity=stock_quantity
            ).calculate_stock_status()

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


class StoreManageView(APIView):
    """
    GET /api/store/manage/
    POST /api/store/manage/
    PATCH /api/store/manage/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        if hasattr(request.user, 'store'):
            serializer = StoreManageSerializer(
                request.user.store,
                context={'request': request},
            )
            return Response({
                'has_store': True,
                'store': serializer.data,
            }, status=status.HTTP_200_OK)

        return Response({
            'has_store': False,
            'store': None,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        if hasattr(request.user, 'store'):
            return Response(
                {'error': 'Store already exists for this account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = StoreManageSerializer(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid store details', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        store = serializer.save(owner=request.user)

        if request.user.account_type != User.AccountType.STORE:
            request.user.account_type = User.AccountType.STORE
            request.user.save(update_fields=['account_type'])

        return Response({
            'has_store': True,
            'store': StoreManageSerializer(
                store,
                context={'request': request},
            ).data,
        }, status=status.HTTP_201_CREATED)

    def patch(self, request):
        if 'logo' in request.data:
            if request.user.account_type != User.AccountType.STORE:
                return Response(
                    {"detail": "You must be a store owner to access this resource."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'Store not found for this account.'},
                status=status.HTTP_404_NOT_FOUND
            )

        store = request.user.store
        serializer = StoreManageSerializer(
            store,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid store details', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            store = serializer.save()
        except (ClientError, BotoCoreError, OSError) as exc:
            return Response(
                {
                    'error': 'Unable to upload logo due to storage configuration.',
                    'details': {'logo': [str(exc)]},
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            'has_store': True,
            'store': StoreManageSerializer(
                store,
                context={'request': request},
            ).data,
        }, status=status.HTTP_200_OK)


class StoreLastImportView(APIView):
    """
    GET /api/store/imports/last/
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request):
        last_import = ProductImportBatch.objects.filter(
            store=request.user.store
        ).first()

        if not last_import:
            return Response({
                'has_import': False,
                'import': None,
            }, status=status.HTTP_200_OK)

        serializer = StoreLastImportSerializer(last_import)
        return Response({
            'has_import': True,
            'import': serializer.data,
        }, status=status.HTTP_200_OK)
