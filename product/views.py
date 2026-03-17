from pathlib import Path

from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter

from api_common.pagination import Paginator
from .filters import ProductBrowseFilter
from .models import Product, StockStatus
from .serializers import ProductBrowseSerializer


class ProductListView(generics.ListAPIView):
    """
    GET /api/products/

    Public product browse endpoint.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductBrowseSerializer
    pagination_class = Paginator
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProductBrowseFilter
    search_fields = ["name"]

    def get_queryset(self):
        queryset = Product.objects.select_related("store")
        params = self.request.query_params

        if "is_active" not in params:
            queryset = queryset.filter(is_active=True)

        if "stock_status" not in params:
            queryset = queryset.exclude(stock_status=StockStatus.OUT_OF_STOCK)

        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    """
    GET /api/products/<uuid>/

    Public product detail endpoint.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductBrowseSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "product_uuid"

    def get_queryset(self):
        return Product.objects.select_related("store").filter(is_active=True)


class ProductTryOnAssetView(APIView):
    """
    GET /api/products/<uuid>/tryon-asset/

    Streams the uploaded product GLB through the API to avoid direct S3 CORS issues.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, product_uuid):
        product = Product.objects.filter(
            uuid=product_uuid,
            is_active=True,
        ).first()
        if product is None or not product.tryon_asset:
            raise Http404("3D asset not found.")

        asset_file = product.tryon_asset.open("rb")
        response = FileResponse(
            asset_file,
            content_type="model/gltf-binary",
            filename=Path(product.tryon_asset.name).name,
        )
        response["Content-Disposition"] = (
            f'inline; filename="{Path(product.tryon_asset.name).name}"'
        )
        return response
