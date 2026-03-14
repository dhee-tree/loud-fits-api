from django.urls import path
from .views import (
    FeedPreviewView,
    FeedImportView,
    StoreProductListView,
    StoreProductDetailView,
    StoreProductImageBatchPreviewView,
    StoreProductImageBatchUploadView,
    StoreManageView,
    StoreLastImportView,
)

urlpatterns = [
    path('products/', StoreProductListView.as_view(), name='store_products'),
    path('products/<uuid:product_uuid>/', StoreProductDetailView.as_view(), name='store_product_detail'),
    path('products/images/preview/', StoreProductImageBatchPreviewView.as_view(), name='store_product_image_batch_preview'),
    path('products/images/upload/', StoreProductImageBatchUploadView.as_view(), name='store_product_image_batch_upload'),
    path('feed/preview/', FeedPreviewView.as_view(), name='feed_preview'),
    path('feed/import/', FeedImportView.as_view(), name='feed_import'),
    path('manage/', StoreManageView.as_view(), name='store_manage'),
    path('imports/last/', StoreLastImportView.as_view(), name='store_last_import'),
]
