from django.urls import path
from .views import WardrobeListCreateView, WardrobeItemDeleteView, StyledWithView

urlpatterns = [
    path('', WardrobeListCreateView.as_view(), name='wardrobe_list_create'),
    path('<uuid:item_uuid>/', WardrobeItemDeleteView.as_view(), name='wardrobe_item_delete'),
    path('styled-with/<uuid:product_uuid>/', StyledWithView.as_view(), name='styled_with'),
]
