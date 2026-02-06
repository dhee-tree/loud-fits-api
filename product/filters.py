from django_filters import rest_framework as filters
from .models import Product, CategoryChoices, StockStatus


class StoreSlugInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class BaseProductFilter(filters.FilterSet):
    category = filters.ChoiceFilter(choices=CategoryChoices.choices)
    is_active = filters.BooleanFilter()
    stock_status = filters.ChoiceFilter(choices=StockStatus.choices)


class ProductBrowseFilter(BaseProductFilter):
    stores = StoreSlugInFilter(field_name="store__slug", lookup_expr="in")

    class Meta:
        model = Product
        fields = ["stores", "category", "is_active", "stock_status"]
