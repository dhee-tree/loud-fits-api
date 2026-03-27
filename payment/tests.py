from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from store.models import Store
from product.models import Product, StockStatus
from order.models import Order, OrderItem
from .models import PayoutMethod, Withdrawal, OrderItemStatusHistory


class PaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store_owner = User.objects.create_user(
            email='storeowner@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        self.store = Store.objects.create(
            owner=self.store_owner,
            name='Payment Store',
            slug='payment-store',
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='testpass123',
        )
        self.product = Product.objects.create(
            store=self.store,
            external_id='PAY-001',
            name='Payment Product',
            category='top',
            image_url='https://example.com/pay.jpg',
            price=Decimal('50.00'),
            currency='GBP',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )

    def _create_order_with_item(self):
        order = Order.objects.create(
            user=self.buyer,
            total=Decimal('50.00'),
            currency='GBP',
            status=Order.Status.PAID,
        )
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            store_name=self.store.name,
            quantity=1,
            price_at_purchase=Decimal('50.00'),
            currency='GBP',
        )
        return order, order_item

    def test_create_payout_method_bank(self):
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.post('/api/store/payments/payout-methods/', {
            'method_type': 'bank_transfer',
            'label': 'Main Business Account',
            'account_holder_name': 'Store Owner',
            'sort_code': '123456',
            'account_number': '12345678',
            'bank_name': 'Test Bank',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['method_type'], 'bank_transfer')
        self.assertEqual(response.data['label'], 'Main Business Account')
        self.assertTrue(response.data['is_default'])

    def test_create_payout_method_paypal(self):
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.post('/api/store/payments/payout-methods/', {
            'method_type': 'paypal',
            'label': 'PayPal Account',
            'account_holder_name': 'Store Owner',
            'paypal_email': 'store@paypal.com',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['method_type'], 'paypal')
        self.assertTrue(response.data['is_default'])

    def test_set_default_payout_method(self):
        self.client.force_authenticate(user=self.store_owner)
        self.client.post('/api/store/payments/payout-methods/', {
            'method_type': 'paypal',
            'label': 'First',
            'account_holder_name': 'Owner',
            'paypal_email': 'first@paypal.com',
        })
        second = self.client.post('/api/store/payments/payout-methods/', {
            'method_type': 'paypal',
            'label': 'Second',
            'account_holder_name': 'Owner',
            'paypal_email': 'second@paypal.com',
        })
        second_uuid = second.data['uuid']

        response = self.client.post(f'/api/store/payments/payout-methods/{second_uuid}/set-default/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_default'])

        first_method = PayoutMethod.objects.filter(store=self.store).exclude(uuid=second_uuid).first()
        self.assertFalse(first_method.is_default)

    def test_get_balance(self):
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.get('/api/store/payments/balance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['available_balance']), Decimal('0'))
        self.assertEqual(Decimal(response.data['pending_balance']), Decimal('0'))
        self.assertEqual(Decimal(response.data['total_earned']), Decimal('0'))

    def test_create_withdrawal_success(self):
        self.client.force_authenticate(user=self.store_owner)
        order, order_item = self._create_order_with_item()
        order_item.store_status = 'completed'
        order_item.price_at_purchase = Decimal('100.00')
        order_item.save(update_fields=['store_status', 'price_at_purchase'])

        payout_method = PayoutMethod.objects.create(
            store=self.store,
            method_type='paypal',
            label='PayPal',
            account_holder_name='Owner',
            paypal_email='owner@paypal.com',
            is_default=True,
        )

        response = self.client.post('/api/store/payments/withdrawals/', {
            'amount': '50.00',
            'payout_method': str(payout_method.uuid),
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['amount']), Decimal('50.00'))

        withdrawal = Withdrawal.objects.get(uuid=response.data['uuid'])
        withdrawal.status = 'completed'
        withdrawal.save(update_fields=['status'])

        balance_response = self.client.get('/api/store/payments/balance/')
        self.assertEqual(Decimal(balance_response.data['available_balance']), Decimal('50.00'))

    def test_create_withdrawal_insufficient_balance(self):
        self.client.force_authenticate(user=self.store_owner)
        order, order_item = self._create_order_with_item()
        order_item.store_status = 'completed'
        order_item.price_at_purchase = Decimal('10.00')
        order_item.save(update_fields=['store_status', 'price_at_purchase'])

        payout_method = PayoutMethod.objects.create(
            store=self.store,
            method_type='paypal',
            label='PayPal',
            account_holder_name='Owner',
            paypal_email='owner@paypal.com',
            is_default=True,
        )

        response = self.client.post('/api/store/payments/withdrawals/', {
            'amount': '50.00',
            'payout_method': str(payout_method.uuid),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_store_orders(self):
        self.client.force_authenticate(user=self.store_owner)
        self._create_order_with_item()

        response = self.client.get('/api/store/payments/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(len(response.data[0]['items']), 1)

    def test_update_order_item_status(self):
        self.client.force_authenticate(user=self.store_owner)
        order, order_item = self._create_order_with_item()

        response = self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/items/{order_item.uuid}/status/',
            {'status': 'processing'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['store_status'], 'processing')

    def test_status_history_created_on_update(self):
        self.client.force_authenticate(user=self.store_owner)
        order, order_item = self._create_order_with_item()

        self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/items/{order_item.uuid}/status/',
            {'status': 'processing', 'note': 'Started processing'},
        )

        history = OrderItemStatusHistory.objects.filter(order_item=order_item)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().status, 'processing')
        self.assertEqual(history.first().note, 'Started processing')

    def test_complete_moves_to_available_balance(self):
        self.client.force_authenticate(user=self.store_owner)
        order, order_item = self._create_order_with_item()

        self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/items/{order_item.uuid}/status/',
            {'status': 'completed'},
        )

        response = self.client.get('/api/store/payments/balance/')
        self.assertEqual(Decimal(response.data['available_balance']), Decimal('50.00'))
        self.assertEqual(Decimal(response.data['pending_balance']), Decimal('0'))

    def test_refund_deducts_balance(self):
        self.client.force_authenticate(user=self.store_owner)
        order, order_item = self._create_order_with_item()

        self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/items/{order_item.uuid}/status/',
            {'status': 'refunded'},
        )

        response = self.client.get('/api/store/payments/balance/')
        self.assertEqual(Decimal(response.data['pending_balance']), Decimal('0'))
        self.assertEqual(Decimal(response.data['available_balance']), Decimal('0'))

    def _create_order_with_multiple_items(self):
        order = Order.objects.create(
            user=self.buyer,
            total=Decimal('120.00'),
            currency='GBP',
            status=Order.Status.PAID,
        )
        item1 = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name='Product A',
            store_name=self.store.name,
            quantity=1,
            price_at_purchase=Decimal('50.00'),
            currency='GBP',
        )
        product2 = Product.objects.create(
            store=self.store,
            external_id='PAY-002',
            name='Product B',
            category='bottom',
            image_url='https://example.com/b.jpg',
            price=Decimal('70.00'),
            currency='GBP',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=5,
        )
        item2 = OrderItem.objects.create(
            order=order,
            product=product2,
            product_name='Product B',
            store_name=self.store.name,
            quantity=1,
            price_at_purchase=Decimal('70.00'),
            currency='GBP',
        )
        return order, item1, item2

    def test_update_order_status_updates_all_items(self):
        self.client.force_authenticate(user=self.store_owner)
        order, item1, item2 = self._create_order_with_multiple_items()

        response = self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/status/',
            {'status': 'processing'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item1.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(item1.store_status, 'processing')
        self.assertEqual(item2.store_status, 'processing')

    def test_update_order_status_only_affects_store_items(self):
        self.client.force_authenticate(user=self.store_owner)
        order, item1, item2 = self._create_order_with_multiple_items()

        other_owner = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        other_store = Store.objects.create(
            owner=other_owner,
            name='Other Store',
            slug='other-store',
        )
        other_product = Product.objects.create(
            store=other_store,
            external_id='OTHER-001',
            name='Other Product',
            category='top',
            image_url='https://example.com/other.jpg',
            price=Decimal('30.00'),
            currency='GBP',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=5,
        )
        other_item = OrderItem.objects.create(
            order=order,
            product=other_product,
            product_name='Other Product',
            store_name=other_store.name,
            quantity=1,
            price_at_purchase=Decimal('30.00'),
            currency='GBP',
        )

        self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/status/',
            {'status': 'shipped', 'note': 'Dispatched'},
        )

        item1.refresh_from_db()
        item2.refresh_from_db()
        other_item.refresh_from_db()
        self.assertEqual(item1.store_status, 'shipped')
        self.assertEqual(item2.store_status, 'shipped')
        self.assertEqual(other_item.store_status, 'pending')

    def test_update_order_status_creates_history_for_each_item(self):
        self.client.force_authenticate(user=self.store_owner)
        order, item1, item2 = self._create_order_with_multiple_items()

        self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/status/',
            {'status': 'processing', 'note': 'Batch update'},
        )

        history1 = OrderItemStatusHistory.objects.filter(order_item=item1)
        history2 = OrderItemStatusHistory.objects.filter(order_item=item2)
        self.assertEqual(history1.count(), 1)
        self.assertEqual(history2.count(), 1)
        self.assertEqual(history1.first().status, 'processing')
        self.assertEqual(history2.first().status, 'processing')
        self.assertEqual(history1.first().note, 'Batch update')
        self.assertEqual(history2.first().note, 'Batch update')

    def test_complete_order_moves_all_to_available(self):
        self.client.force_authenticate(user=self.store_owner)
        order, item1, item2 = self._create_order_with_multiple_items()

        self.client.patch(
            f'/api/store/payments/orders/{order.uuid}/status/',
            {'status': 'completed'},
        )

        response = self.client.get('/api/store/payments/balance/')
        self.assertEqual(Decimal(response.data['available_balance']), Decimal('120.00'))
        self.assertEqual(Decimal(response.data['pending_balance']), Decimal('0'))
