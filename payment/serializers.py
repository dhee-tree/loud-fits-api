import re
from decimal import Decimal
from django.db.models import Sum, F
from rest_framework import serializers
from order.models import OrderItem, Order
from .models import PayoutMethod, Withdrawal, OrderItemStatusHistory


class PayoutMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutMethod
        fields = [
            'uuid', 'method_type', 'label', 'bank_name', 'account_holder_name',
            'sort_code', 'account_number', 'iban', 'paypal_email',
            'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'is_default', 'created_at', 'updated_at']

    def validate_sort_code(self, value):
        if value and not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError('Sort code must be exactly 6 digits.')
        return value

    def validate_account_number(self, value):
        if value and not re.match(r'^\d{8}$', value):
            raise serializers.ValidationError('Account number must be exactly 8 digits.')
        return value

    def validate(self, data):
        method_type = data.get('method_type', getattr(self.instance, 'method_type', None))

        if method_type == PayoutMethod.MethodType.BANK_TRANSFER:
            if not data.get('account_holder_name', getattr(self.instance, 'account_holder_name', '')):
                raise serializers.ValidationError({'account_holder_name': 'This field is required for bank transfer.'})
            if not data.get('account_number', getattr(self.instance, 'account_number', '')):
                raise serializers.ValidationError({'account_number': 'This field is required for bank transfer.'})
            if not data.get('sort_code', getattr(self.instance, 'sort_code', '')):
                raise serializers.ValidationError({'sort_code': 'This field is required for bank transfer.'})

        if method_type == PayoutMethod.MethodType.PAYPAL:
            if not data.get('paypal_email', getattr(self.instance, 'paypal_email', '')):
                raise serializers.ValidationError({'paypal_email': 'This field is required for PayPal.'})

        return data


class StoreBalanceSerializer(serializers.Serializer):
    pending_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_earned = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)


class OrderItemStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemStatusHistory
        fields = ['uuid', 'status', 'changed_by', 'note', 'created_at']
        read_only_fields = fields


class OrderItemStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderItem.StoreStatus.choices)
    note = serializers.CharField(required=False, default='')


class StoreOrderItemSerializer(serializers.ModelSerializer):
    status_history = OrderItemStatusHistorySerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'uuid', 'product_name', 'store_name', 'quantity',
            'price_at_purchase', 'currency', 'store_status',
            'image_url', 'status_history',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if hasattr(obj.product, 'get_image_url'):
            return obj.product.get_image_url(request=request)
        return None


class StoreOrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['uuid', 'status', 'total', 'currency', 'items', 'created_at', 'updated_at']

    def get_items(self, obj):
        store = self.context.get('store')
        items = obj.items.filter(product__store=store).prefetch_related('status_history')
        return StoreOrderItemSerializer(items, many=True, context=self.context).data


class WithdrawalSerializer(serializers.ModelSerializer):
    payout_method_label = serializers.CharField(source='payout_method.label', read_only=True, default='')

    class Meta:
        model = Withdrawal
        fields = [
            'uuid', 'payout_method_label', 'amount', 'status',
            'reference', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class WithdrawalCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payout_method = serializers.UUIDField()

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate(self, data):
        store = self.context.get('store')

        try:
            payout_method = PayoutMethod.objects.get(uuid=data['payout_method'], store=store)
        except PayoutMethod.DoesNotExist:
            raise serializers.ValidationError({'payout_method': 'Payout method not found.'})

        data['payout_method_obj'] = payout_method

        completed = OrderItem.objects.filter(
            product__store=store,
            store_status='completed',
        ).aggregate(
            total=Sum(F('price_at_purchase') * F('quantity'))
        )['total'] or Decimal('0')

        withdrawn_or_pending = Withdrawal.objects.filter(
            store=store,
        ).exclude(
            status='rejected',
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        available_balance = completed - withdrawn_or_pending
        if data['amount'] > available_balance:
            raise serializers.ValidationError({'amount': 'Insufficient available balance.'})

        return data
