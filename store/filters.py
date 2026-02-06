from django_filters import rest_framework as filters
from product.filters import BaseProductFilter
from product.models import Product


class StoreProductFilter(BaseProductFilter):
    class Meta:
        model = Product
        fields = ["category", "is_active", "stock_status"]
