from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from user.models import User
from store.models import Store
from product.models import Product, StockStatus
from order.models import Order, OrderItem
from outfit.models import Outfit, OutfitItem
from .models import WardrobeItem


class WardrobeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='wardrobe@example.com', password='testpass123')
        self.creator = User.objects.create_user(email='creator_w@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.creator, name='W Store', slug='w-store')
        self.product = Product.objects.create(
            store=self.store, external_id='W-001', name='Blue Jeans',
            category='bottom', image_url='https://example.com/jeans.jpg',
            price=45.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )

    def test_wardrobe_empty(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/wardrobe/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_add_to_wardrobe_manually(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/wardrobe/', {'product_id': str(self.product.uuid)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source'], 'manual')

    def test_add_duplicate_idempotent(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/wardrobe/', {'product_id': str(self.product.uuid)})
        response = self.client.post('/api/wardrobe/', {'product_id': str(self.product.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WardrobeItem.objects.filter(user=self.user).count(), 1)

    def test_remove_from_wardrobe(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/wardrobe/', {'product_id': str(self.product.uuid)})
        response = self.client.delete(f'/api/wardrobe/{res.data["uuid"]}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WardrobeItem.objects.filter(user=self.user).count(), 0)

    def test_checkout_adds_to_wardrobe(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/cart/items/', {'product_id': str(self.product.uuid)})
        self.client.post('/api/orders/checkout/')
        self.assertTrue(
            WardrobeItem.objects.filter(user=self.user, product=self.product, source='purchased').exists()
        )

    def test_styled_with(self):
        self.client.force_authenticate(user=self.user)
        outfit = Outfit.objects.create(
            owner=self.creator, status=Outfit.Status.PUBLISHED,
            title='Styled', published_at=timezone.now(),
        )
        top = Product.objects.create(
            store=self.store, external_id='W-002', name='White Tee',
            category='top', image_url='https://example.com/tee.jpg',
            price=25.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        OutfitItem.objects.create(
            outfit=outfit, slot='bottom', product=self.product,
            product_name=self.product.name, image_url_used=self.product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.product.price, currency=self.product.currency,
        )
        OutfitItem.objects.create(
            outfit=outfit, slot='top', product=top,
            product_name=top.name, image_url_used=top.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=top.price, currency=top.currency,
        )

        response = self.client.get(f'/api/wardrobe/styled-with/{self.product.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_unauthenticated(self):
        response = self.client.get('/api/wardrobe/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
