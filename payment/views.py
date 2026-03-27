from decimal import Decimal
from django.db.models import Sum, F
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from store.permissions import IsStoreOwner
from order.models import Order, OrderItem
from .models import PayoutMethod, Withdrawal, OrderItemStatusHistory
from .serializers import (
    PayoutMethodSerializer,
    StoreBalanceSerializer,
    WithdrawalSerializer,
    WithdrawalCreateSerializer,
    StoreOrderSerializer,
    StoreOrderItemSerializer,
    OrderItemStatusUpdateSerializer,
)


class PayoutMethodListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        payout_methods = PayoutMethod.objects.filter(store=request.user.store)
        serializer = PayoutMethodSerializer(payout_methods, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PayoutMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_first = not PayoutMethod.objects.filter(store=request.user.store).exists()
        payout_method = serializer.save(store=request.user.store, is_default=is_first)

        return Response(
            PayoutMethodSerializer(payout_method).data,
            status=status.HTTP_201_CREATED,
        )


class PayoutMethodDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get_object(self, request, payout_method_uuid):
        return get_object_or_404(PayoutMethod, uuid=payout_method_uuid, store=request.user.store)

    def get(self, request, payout_method_uuid):
        payout_method = self.get_object(request, payout_method_uuid)
        serializer = PayoutMethodSerializer(payout_method)
        return Response(serializer.data)

    def put(self, request, payout_method_uuid):
        payout_method = self.get_object(request, payout_method_uuid)
        serializer = PayoutMethodSerializer(payout_method, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PayoutMethodSerializer(payout_method).data)

    def patch(self, request, payout_method_uuid):
        payout_method = self.get_object(request, payout_method_uuid)
        serializer = PayoutMethodSerializer(payout_method, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PayoutMethodSerializer(payout_method).data)

    def delete(self, request, payout_method_uuid):
        payout_method = self.get_object(request, payout_method_uuid)
        was_default = payout_method.is_default
        payout_method.delete()

        if was_default:
            next_method = PayoutMethod.objects.filter(store=request.user.store).first()
            if next_method:
                next_method.is_default = True
                next_method.save(update_fields=['is_default'])

        return Response(status=status.HTTP_204_NO_CONTENT)


class PayoutMethodSetDefaultView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def post(self, request, payout_method_uuid):
        payout_method = get_object_or_404(PayoutMethod, uuid=payout_method_uuid, store=request.user.store)

        PayoutMethod.objects.filter(store=request.user.store, is_default=True).update(is_default=False)
        payout_method.is_default = True
        payout_method.save(update_fields=['is_default'])

        return Response(PayoutMethodSerializer(payout_method).data)


class StoreBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        store = request.user.store

        store_items = OrderItem.objects.filter(product__store=store)

        pending = store_items.filter(
            store_status__in=['pending', 'processing', 'shipped']
        ).aggregate(
            total=Sum(F('price_at_purchase') * F('quantity'))
        )['total'] or Decimal('0')

        completed = store_items.filter(
            store_status='completed'
        ).aggregate(
            total=Sum(F('price_at_purchase') * F('quantity'))
        )['total'] or Decimal('0')

        withdrawn_or_pending = Withdrawal.objects.filter(
            store=store,
        ).exclude(
            status='rejected',
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        available = completed - withdrawn_or_pending
        total_earned = completed

        serializer = StoreBalanceSerializer({
            'pending_balance': pending,
            'available_balance': available,
            'total_earned': total_earned,
            'currency': 'GBP',
        })
        return Response(serializer.data)


class WithdrawalListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        withdrawals = Withdrawal.objects.filter(store=request.user.store).select_related('payout_method')
        serializer = WithdrawalSerializer(withdrawals, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WithdrawalCreateSerializer(
            data=request.data,
            context={'store': request.user.store},
        )
        serializer.is_valid(raise_exception=True)

        withdrawal = Withdrawal.objects.create(
            store=request.user.store,
            payout_method=serializer.validated_data['payout_method_obj'],
            amount=serializer.validated_data['amount'],
        )

        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED,
        )


class StoreOrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        store = request.user.store
        orders = Order.objects.filter(
            items__product__store=store,
        ).distinct().prefetch_related('items__product__store', 'items__status_history')

        store_status = request.query_params.get('store_status')
        if store_status:
            orders = orders.filter(items__store_status=store_status, items__product__store=store).distinct()

        serializer = StoreOrderSerializer(
            orders, many=True,
            context={'request': request, 'store': store},
        )
        return Response(serializer.data)


class StoreOrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request, order_uuid):
        store = request.user.store
        try:
            order = Order.objects.filter(
                items__product__store=store,
            ).distinct().prefetch_related('items__product__store', 'items__status_history').get(uuid=order_uuid)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = StoreOrderSerializer(
            order,
            context={'request': request, 'store': store},
        )
        return Response(serializer.data)


class OrderItemStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def patch(self, request, order_uuid, item_uuid):
        store = request.user.store

        try:
            order_item = OrderItem.objects.select_related('product__store').get(
                uuid=item_uuid,
                order__uuid=order_uuid,
                product__store=store,
            )
        except OrderItem.DoesNotExist:
            return Response({'detail': 'Order item not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderItemStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        note = serializer.validated_data.get('note', '')

        order_item.store_status = new_status
        order_item.save(update_fields=['store_status'])

        OrderItemStatusHistory.objects.create(
            order_item=order_item,
            status=new_status,
            changed_by=request.user,
            note=note,
        )

        response_serializer = StoreOrderItemSerializer(
            order_item,
            context={'request': request},
        )
        return Response(response_serializer.data)


class StoreOrderStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def patch(self, request, order_uuid):
        store = request.user.store

        try:
            order = Order.objects.filter(
                items__product__store=store,
            ).distinct().prefetch_related('items__product__store', 'items__status_history').get(uuid=order_uuid)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderItemStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        note = serializer.validated_data.get('note', '')

        store_items = OrderItem.objects.select_related('product__store').filter(
            order=order,
            product__store=store,
        )

        for item in store_items:
            item.store_status = new_status
            item.save(update_fields=['store_status'])

            OrderItemStatusHistory.objects.create(
                order_item=item,
                status=new_status,
                changed_by=request.user,
                note=note,
            )

        response_serializer = StoreOrderSerializer(
            order,
            context={'request': request, 'store': store},
        )
        return Response(response_serializer.data)
