from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Address
from .serializers import AddressSerializer


class AddressListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_first = not Address.objects.filter(user=request.user).exists()
        address = serializer.save(user=request.user, is_default=is_first)

        return Response(
            AddressSerializer(address).data,
            status=status.HTTP_201_CREATED,
        )


class AddressDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, address_uuid):
        return get_object_or_404(Address, uuid=address_uuid, user=request.user)

    def patch(self, request, address_uuid):
        address = self.get_object(request, address_uuid)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AddressSerializer(address).data)

    def delete(self, request, address_uuid):
        address = self.get_object(request, address_uuid)
        was_default = address.is_default
        address.delete()

        if was_default:
            next_address = Address.objects.filter(user=request.user).first()
            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=['is_default'])

        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressSetDefaultView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, address_uuid):
        address = get_object_or_404(Address, uuid=address_uuid, user=request.user)

        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save(update_fields=['is_default'])

        return Response(AddressSerializer(address).data)
