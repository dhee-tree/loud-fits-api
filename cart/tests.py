from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from product.models import Product, StockStatus
from store.models import Store
from .models import Cart, CartItem


class CartTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='shopper@example.com', password='testpass123')
        self.store_owner = User.objects.create_user(email='seller@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.store_owner, name='Cart Store', slug='cart-store')
        self.product = Product.objects.create(
            store=self.store, external_id='CART-001', name='Cart Product',
            category='top', image_url='https://example.com/product.jpg',
            price=29.99, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.product2 = Product.objects.create(
            store=self.store, external_id='CART-002', name='Cart Product 2',
            category='bottom', image_url='https://example.com/product2.jpg',
            price=49.99, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=5,
        )

    def test_get_cart_empty(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['item_count'], 0)
        self.assertEqual(len(response.data['items']), 0)

    def test_add_to_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['item_count'], 1)

    def test_add_same_product_increments_quantity(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        response = self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['item_count'], 2)

    def test_update_quantity(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.first()
        response = self.client.patch(f'/api/cart/items/{item.uuid}/', {'quantity': 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['item_count'], 3)

    def test_remove_item(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.first()
        response = self.client.delete(f'/api/cart/items/{item.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(cart.items.count(), 0)

    def test_clear_cart(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        self.client.post('/api/cart/items/', {'product_id': str(self.product2.uuid)})
        response = self.client.delete('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

    def test_add_invalid_product(self):
        self.client.force_authenticate(user=self.user)
        import uuid
        response = self.client.post('/api/cart/items/', {'product_id': str(uuid.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated(self):
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
