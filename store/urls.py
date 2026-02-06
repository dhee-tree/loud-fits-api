from django.urls import path
from .views import FeedPreviewView, FeedImportView, StoreProductListView

urlpatterns = [
    path('products/', StoreProductListView.as_view(), name='store_products'),
    path('feed/preview/', FeedPreviewView.as_view(), name='feed_preview'),
    path('feed/import/', FeedImportView.as_view(), name='feed_import'),
]
