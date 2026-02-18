from django.urls import path

from .views import (
    CurrentDraftView,
    OutfitDetailView,
    OutfitListCreateView,
    OutfitModerationView,
    OutfitPublishView,
    OutfitSlotItemView,
)


urlpatterns = [
    path('', OutfitListCreateView.as_view(), name='outfit_list_create'),
    path('current-draft/', CurrentDraftView.as_view(), name='current_draft'),
    path('<uuid:outfit_uuid>/', OutfitDetailView.as_view(), name='outfit_detail'),
    path('<uuid:outfit_uuid>/publish/', OutfitPublishView.as_view(), name='outfit_publish'),
    path(
        '<uuid:outfit_uuid>/moderation/',
        OutfitModerationView.as_view(),
        name='outfit_moderation',
    ),
    path(
        '<uuid:outfit_uuid>/items/<str:slot>/',
        OutfitSlotItemView.as_view(),
        name='outfit_slot_item',
    ),
]
