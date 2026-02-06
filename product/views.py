from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions
from rest_framework.filters import SearchFilter

from api_common.pagination import Paginator
from .filters import ProductBrowseFilter
from .models import Product, StockStatus
from .serializers import ProductListSerializer


class ProductListView(generics.ListAPIView):
    """
    GET /api/products/

    Public product browse endpoint.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer
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
