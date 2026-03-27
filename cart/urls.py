from django.urls import path
from .views import CartView, CartItemView

urlpatterns = [
    path('', CartView.as_view(), name='cart'),
    path('items/', CartItemView.as_view(), name='cart_add_item'),
    path('items/<uuid:item_uuid>/', CartItemView.as_view(), name='cart_item_detail'),
]
