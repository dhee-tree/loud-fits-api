from django.urls import path
from .views import CheckoutView, OrderListView, OrderDetailView

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('', OrderListView.as_view(), name='order_list'),
    path('<uuid:order_uuid>/', OrderDetailView.as_view(), name='order_detail'),
]
