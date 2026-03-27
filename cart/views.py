from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from outfit.models import Outfit
from product.models import Product
from .models import Cart, CartItem, CartAddEvent
from .serializers import CartSerializer, AddToCartSerializer


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        product = Product.objects.get(uuid=serializer.validated_data['product_id'])
        quantity = serializer.validated_data['quantity']

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=['quantity'])

        outfit_uuid = serializer.validated_data.get('outfit_uuid')
        if outfit_uuid:
            outfit = Outfit.objects.get(uuid=outfit_uuid)
            CartAddEvent.objects.create(user=request.user, outfit=outfit)

        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def patch(self, request, item_uuid):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        try:
            item = cart.items.get(uuid=item_uuid)
        except CartItem.DoesNotExist:
            return Response({'detail': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)

        quantity = request.data.get('quantity')
        if quantity is not None:
            if int(quantity) < 1:
                return Response({'quantity': ['Must be at least 1.']}, status=status.HTTP_400_BAD_REQUEST)
            item.quantity = int(quantity)
            item.save(update_fields=['quantity'])

        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)

    def delete(self, request, item_uuid):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.filter(uuid=item_uuid).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
