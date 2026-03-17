from django.urls import path
from .views import ProductDetailView, ProductListView, ProductTryOnAssetView


urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('<uuid:product_uuid>/', ProductDetailView.as_view(), name='product_detail'),
    path('<uuid:product_uuid>/tryon-asset/', ProductTryOnAssetView.as_view(), name='product_tryon_asset'),
]
