from django.urls import path
from .views import FeedPreviewView, FeedImportView

urlpatterns = [
    path('feed/preview/', FeedPreviewView.as_view(), name='feed_preview'),
    path('feed/import/', FeedImportView.as_view(), name='feed_import'),
]
