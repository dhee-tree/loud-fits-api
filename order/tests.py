from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from product.models import Product, StockStatus
from store.models import Store
from cart.models import Cart, CartItem
from .models import Order


class CheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='buyer@example.com', password='testpass123')
        self.store_owner = User.objects.create_user(email='seller@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.store_owner, name='Order Store', slug='order-store')
        self.product = Product.objects.create(
            store=self.store, external_id='ORD-001', name='Order Product',
            category='top', image_url='https://example.com/order.jpg',
            price=29.99, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )

    def test_checkout_success(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'paid')
        self.assertEqual(len(response.data['items']), 1)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_empty_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_unauthenticated(self):
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_order_list(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        self.client.post('/api/orders/checkout/')
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_order_detail(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        checkout = self.client.post('/api/orders/checkout/')
        order_id = checkout.data['uuid']
        response = self.client.get(f'/api/orders/{order_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], order_id)
