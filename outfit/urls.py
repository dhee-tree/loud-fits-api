from django.urls import path

from .views import CurrentDraftView, OutfitDetailView, OutfitListCreateView, OutfitSlotItemView


urlpatterns = [
    path('', OutfitListCreateView.as_view(), name='outfit_list_create'),
    path('current-draft/', CurrentDraftView.as_view(), name='current_draft'),
    path('<uuid:outfit_uuid>/', OutfitDetailView.as_view(), name='outfit_detail'),
    path(
        '<uuid:outfit_uuid>/items/<str:slot>/',
        OutfitSlotItemView.as_view(),
        name='outfit_slot_item',
    ),
]
