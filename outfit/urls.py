from django.urls import path

from .views import (
    CurrentDraftView,
    OutfitDetailView,
    OutfitLikeView,
    OutfitListCreateView,
    OutfitModerationView,
    OutfitPublishView,
    OutfitSaveView,
    OutfitSlotItemView,
    OutfitUnpublishView,
)


urlpatterns = [
    path('', OutfitListCreateView.as_view(), name='outfit_list_create'),
    path('current-draft/', CurrentDraftView.as_view(), name='current_draft'),
    path('<uuid:outfit_uuid>/', OutfitDetailView.as_view(), name='outfit_detail'),
    path('<uuid:outfit_uuid>/publish/', OutfitPublishView.as_view(), name='outfit_publish'),
    path('<uuid:outfit_uuid>/unpublish/', OutfitUnpublishView.as_view(), name='outfit_unpublish'),
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
    path('<uuid:outfit_uuid>/like/', OutfitLikeView.as_view(), name='outfit_like'),
    path('<uuid:outfit_uuid>/save/', OutfitSaveView.as_view(), name='outfit_save'),
]
