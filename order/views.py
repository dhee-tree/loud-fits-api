from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from cart.models import Cart
from wardrobe.models import WardrobeItem
from .models import Order, OrderItem
from .serializers import OrderSerializer


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.prefetch_related('items__product__store').get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'detail': 'Your bag is empty.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items = cart.items.select_related('product__store').all()
        if not cart_items.exists():
            return Response(
                {'detail': 'Your bag is empty.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = sum(item.product.price * item.quantity for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            total=total,
            currency=cart_items.first().product.currency or 'GBP',
            status=Order.Status.PAID,
        )

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                store_name=cart_item.product.store.name,
                quantity=cart_item.quantity,
                price_at_purchase=cart_item.product.price,
                currency=cart_item.product.currency or 'GBP',
            )

        for cart_item in cart_items:
            WardrobeItem.objects.get_or_create(
                user=request.user,
                product=cart_item.product,
                defaults={'source': WardrobeItem.Source.PURCHASED},
            )

        cart.items.all().delete()

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)


class OrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_uuid):
        try:
            order = Order.objects.prefetch_related('items__product').get(
                uuid=order_uuid, user=request.user,
            )
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)
