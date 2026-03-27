from django.urls import path
from .views import AddressListCreateView, AddressDetailView, AddressSetDefaultView

urlpatterns = [
    path('', AddressListCreateView.as_view(), name='address_list_create'),
    path('<uuid:address_uuid>/', AddressDetailView.as_view(), name='address_detail'),
    path('<uuid:address_uuid>/set-default/', AddressSetDefaultView.as_view(), name='address_set_default'),
]
