from django.urls import path
from .views import ProductListView, ProductTryOnAssetView


urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('<uuid:product_uuid>/tryon-asset/', ProductTryOnAssetView.as_view(), name='product_tryon_asset'),
]
