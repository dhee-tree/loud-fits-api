from django.urls import path
from .views import (
    PayoutMethodListCreateView,
    PayoutMethodDetailView,
    PayoutMethodSetDefaultView,
    StoreBalanceView,
    WithdrawalListCreateView,
    StoreOrderListView,
    StoreOrderDetailView,
    OrderItemStatusUpdateView,
    StoreOrderStatusUpdateView,
)

urlpatterns = [
    path('payout-methods/', PayoutMethodListCreateView.as_view(), name='payout_method_list_create'),
    path('payout-methods/<uuid:payout_method_uuid>/', PayoutMethodDetailView.as_view(), name='payout_method_detail'),
    path('payout-methods/<uuid:payout_method_uuid>/set-default/', PayoutMethodSetDefaultView.as_view(), name='payout_method_set_default'),
    path('balance/', StoreBalanceView.as_view(), name='store_balance'),
    path('withdrawals/', WithdrawalListCreateView.as_view(), name='withdrawal_list_create'),
    path('orders/', StoreOrderListView.as_view(), name='store_order_list'),
    path('orders/<uuid:order_uuid>/', StoreOrderDetailView.as_view(), name='store_order_detail'),
    path('orders/<uuid:order_uuid>/items/<uuid:item_uuid>/status/', OrderItemStatusUpdateView.as_view(), name='order_item_status_update'),
    path('orders/<uuid:order_uuid>/status/', StoreOrderStatusUpdateView.as_view(), name='store_order_status_update'),
]
