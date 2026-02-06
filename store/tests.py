import json
from io import BytesIO
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from store.models import Store
from product.models import Product, ProductImportBatch, StockStatus


class StoreTestCase(TestCase):
    """Base test class with common setup for store tests."""

    def setUp(self):
        self.client = APIClient()

    def create_store_user(self, email='store@example.com', password='testpass123', store_slug='test-store'):
        """Create a user with account_type=Store and an associated Store."""
        user = User.objects.create_user(
            email=email,
            password=password,
            account_type=User.AccountType.STORE
        )
        store = Store.objects.create(
            owner=user,
            name='Test Store',
            slug=store_slug
        )
        return user, store

    def create_regular_user(self, email='user@example.com', password='testpass123'):
        """Create a regular user without store access."""
        return User.objects.create_user(
            email=email,
            password=password,
            account_type=User.AccountType.USER
        )

    def get_valid_feed(self):
        """Return a valid product feed."""
        return {
            'products': [
                {
                    'external_id': 'PROD001',
                    'name': 'Blue T-Shirt',
                    'category': 'top',
                    'image_url': 'https://example.com/images/blue-tshirt.jpg',
                    'price': 29.99,
                    'currency': 'GBP',
                    'product_url': 'https://example.com/products/blue-tshirt'
                },
                {
                    'external_id': 'PROD002',
                    'name': 'Black Jeans',
                    'category': 'bottom',
                    'image_url': 'https://example.com/images/black-jeans.jpg',
                    'price': 59.99,
                    'currency': 'GBP',
                    'product_url': 'https://example.com/products/black-jeans'
                }
            ]
        }


class FeedPreviewTests(StoreTestCase):
    """Tests for the feed preview endpoint."""

    def setUp(self):
        super().setUp()
        self.url = '/api/store/feed/preview/'
        self.user, self.store = self.create_store_user()

    def test_preview_requires_authentication(self):
        """Test that unauthenticated requests are rejected."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_preview_requires_store_account(self):
        """Test that non-store users are rejected."""
        regular_user = self.create_regular_user()
        self.client.force_authenticate(user=regular_user)

        response = self.client.post(
            self.url, self.get_valid_feed(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_preview_valid_feed(self):
        """Test successful preview of a valid feed."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url, self.get_valid_feed(), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_valid'])
        self.assertEqual(response.data['total_products'], 2)
        self.assertEqual(response.data['valid_count'], 2)
        self.assertEqual(response.data['failed_count'], 0)
        self.assertEqual(response.data['counts_by_category'], {
                         'top': 1, 'bottom': 1})
        self.assertEqual(len(response.data['sample_products']), 2)
        self.assertEqual(response.data['errors'], [])

    def test_preview_with_invalid_category(self):
        """Test preview catches invalid category values."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Test Product',
                'category': 'invalid_category',
                'image_url': 'https://example.com/image.jpg',
                'price': 10.00,
                'currency': 'GBP',
                'product_url': 'https://example.com/product'
            }]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_valid'])
        self.assertEqual(response.data['failed_count'], 1)
        self.assertEqual(len(response.data['errors']), 1)
        self.assertEqual(response.data['errors'][0]['external_id'], 'PROD001')

    def test_preview_with_invalid_urls(self):
        """Test preview catches invalid URLs."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Test Product',
                'category': 'top',
                'image_url': 'not-a-valid-url',
                'price': 10.00,
                'currency': 'GBP',
                'product_url': 'also-not-valid'
            }]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_valid'])
        self.assertEqual(response.data['failed_count'], 1)

    def test_preview_with_missing_fields(self):
        """Test preview catches missing required fields."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Test Product'
                # Missing: category, image_url, price, currency, product_url
            }]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_valid'])
        self.assertEqual(response.data['failed_count'], 1)
        # Should have errors for missing fields
        error_fields = [e['field']
                        for e in response.data['errors'][0]['errors']]
        self.assertIn('category', error_fields)
        self.assertIn('image_url', error_fields)

    def test_preview_with_duplicate_ids(self):
        """Test preview detects duplicate product IDs."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [
                {
                    'external_id': 'PROD001',
                    'name': 'Product One',
                    'category': 'top',
                    'image_url': 'https://example.com/img1.jpg',
                    'price': 10.00,
                    'currency': 'GBP',
                    'product_url': 'https://example.com/prod1'
                },
                {
                    'external_id': 'PROD001',  # Duplicate ID
                    'name': 'Product Two',
                    'category': 'bottom',
                    'image_url': 'https://example.com/img2.jpg',
                    'price': 20.00,
                    'currency': 'GBP',
                    'product_url': 'https://example.com/prod2'
                }
            ]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_valid'])
        # First product is valid, second is duplicate
        self.assertEqual(response.data['valid_count'], 1)
        self.assertEqual(response.data['failed_count'], 1)

    def test_preview_with_negative_price(self):
        """Test preview catches negative prices."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Test Product',
                'category': 'top',
                'image_url': 'https://example.com/image.jpg',
                'price': -10.00,
                'currency': 'GBP',
                'product_url': 'https://example.com/product'
            }]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_valid'])

    def test_preview_empty_products_array(self):
        """Test preview rejects empty products array."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, {'products': []}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_no_products_key(self):
        """Test preview rejects feed without products key."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, {'data': []}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_with_file_upload(self):
        """Test preview accepts multipart file upload."""
        self.client.force_authenticate(user=self.user)

        feed_content = json.dumps(self.get_valid_feed()).encode('utf-8')
        feed_file = BytesIO(feed_content)
        feed_file.name = 'feed.json'

        response = self.client.post(
            self.url,
            {'feed': feed_file},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_valid'])


class FeedImportTests(StoreTestCase):
    """Tests for the feed import endpoint."""

    def setUp(self):
        super().setUp()
        self.url = '/api/store/feed/import/'
        self.user, self.store = self.create_store_user()

    def test_import_requires_authentication(self):
        """Test that unauthenticated requests are rejected."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_import_requires_store_account(self):
        """Test that non-store users are rejected."""
        regular_user = self.create_regular_user()
        self.client.force_authenticate(user=regular_user)

        response = self.client.post(
            self.url, self.get_valid_feed(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_import_creates_new_products(self):
        """Test successful import creates new products."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url, self.get_valid_feed(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['imported'], 2)
        self.assertEqual(response.data['updated'], 0)
        self.assertEqual(response.data['failed'], 0)

        # Verify products were created in database
        self.assertEqual(Product.objects.filter(store=self.store).count(), 2)

        # Verify product data
        product = Product.objects.get(store=self.store, external_id='PROD001')
        self.assertEqual(product.name, 'Blue T-Shirt')
        self.assertEqual(product.category, 'top')
        self.assertEqual(float(product.price), 29.99)

    def test_import_updates_existing_products(self):
        """Test import updates existing products (upsert)."""
        self.client.force_authenticate(user=self.user)

        # First import
        self.client.post(self.url, self.get_valid_feed(), format='json')

        # Second import with updated data
        updated_feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Updated Blue T-Shirt',
                'category': 'top',
                'image_url': 'https://example.com/images/updated.jpg',
                'price': 34.99,
                'currency': 'GBP',
                'product_url': 'https://example.com/products/blue-tshirt'
            }]
        }

        response = self.client.post(self.url, updated_feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported'], 0)
        self.assertEqual(response.data['updated'], 1)

        # Verify product was updated
        product = Product.objects.get(store=self.store, external_id='PROD001')
        self.assertEqual(product.name, 'Updated Blue T-Shirt')
        self.assertEqual(float(product.price), 34.99)

    def test_import_creates_batch_record(self):
        """Test import creates a ProductImportBatch record."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url, self.get_valid_feed(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('batch_id', response.data)

        # Verify batch was created
        batch = ProductImportBatch.objects.get(uuid=response.data['batch_id'])
        self.assertEqual(batch.store, self.store)
        self.assertEqual(batch.uploaded_by, self.user)
        self.assertEqual(batch.total, 2)
        self.assertEqual(batch.imported, 2)
        self.assertEqual(batch.updated, 0)
        self.assertEqual(batch.failed, 0)

    def test_import_updates_store_timestamp(self):
        """Test import updates store's feed_last_uploaded_at."""
        self.client.force_authenticate(user=self.user)

        self.assertIsNone(self.store.feed_last_uploaded_at)

        response = self.client.post(
            self.url, self.get_valid_feed(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.store.refresh_from_db()
        self.assertIsNotNone(self.store.feed_last_uploaded_at)

    def test_import_with_partial_failures(self):
        """Test import handles mix of valid and invalid products."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [
                {
                    'external_id': 'PROD001',
                    'name': 'Valid Product',
                    'category': 'top',
                    'image_url': 'https://example.com/image.jpg',
                    'price': 10.00,
                    'currency': 'GBP',
                    'product_url': 'https://example.com/product'
                },
                {
                    'external_id': 'PROD002',
                    'name': 'Invalid Product',
                    'category': 'invalid',
                    'image_url': 'not-a-url',
                    'price': -5.00,
                    'currency': 'X',
                    'product_url': 'also-invalid'
                }
            ]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['imported'], 1)
        self.assertEqual(response.data['failed'], 1)
        self.assertEqual(len(response.data['errors']), 1)

        # Only valid product should be in database
        self.assertEqual(Product.objects.filter(store=self.store).count(), 1)

    def test_import_store_isolation(self):
        """Test that stores can only import to their own store."""
        self.client.force_authenticate(user=self.user)

        # Create another store user with a different slug
        other_user, other_store = self.create_store_user(
            email='other@example.com',
            store_slug='other-store'
        )

        # Import with first user
        self.client.post(self.url, self.get_valid_feed(), format='json')

        # Login as second user and import same products
        self.client.force_authenticate(user=other_user)
        self.client.post(self.url, self.get_valid_feed(), format='json')

        # Each store should have their own products
        self.assertEqual(Product.objects.filter(store=self.store).count(), 2)
        self.assertEqual(Product.objects.filter(store=other_store).count(), 2)

        # Total products should be 4
        self.assertEqual(Product.objects.count(), 4)

    def test_import_with_file_upload(self):
        """Test import accepts multipart file upload."""
        self.client.force_authenticate(user=self.user)

        feed_content = json.dumps(self.get_valid_feed()).encode('utf-8')
        feed_file = BytesIO(feed_content)
        feed_file.name = 'feed.json'

        response = self.client.post(
            self.url,
            {'feed': feed_file},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported'], 2)


class StoreProductListTests(StoreTestCase):
    """Tests for the store product list endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/api/store/products/"
        self.user, self.store = self.create_store_user()
        self.other_user, self.other_store = self.create_store_user(
            email="other@example.com",
            store_slug="other-store",
        )

        Product.objects.create(
            store=self.store,
            external_id="EXT-001",
            name="Blue Tee",
            category="top",
            image_url="https://example.com/blue.jpg",
            price=19.99,
            currency="GBP",
            product_url="https://example.com/blue",
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=15,
        )
        Product.objects.create(
            store=self.store,
            external_id="EXT-002",
            name="Black Jeans",
            category="bottom",
            image_url="https://example.com/black.jpg",
            price=49.99,
            currency="GBP",
            product_url="https://example.com/black",
            is_active=False,
            stock_status=StockStatus.OUT_OF_STOCK,
            stock_quantity=0,
        )
        Product.objects.create(
            store=self.other_store,
            external_id="EXT-003",
            name="Other Store Tee",
            category="top",
            image_url="https://example.com/other.jpg",
            price=9.99,
            currency="GBP",
            product_url="https://example.com/other",
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=8,
        )

    def test_products_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_products_requires_store_account(self):
        regular_user = self.create_regular_user()
        self.client.force_authenticate(user=regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_products_lists_store_products_only(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        external_ids = {item["external_id"] for item in response.data["results"]}
        self.assertSetEqual(external_ids, {"EXT-001", "EXT-002"})

    def test_products_filters_search_and_category(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?search=EXT-001&category=top")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["external_id"], "EXT-001")

    def test_products_filters_is_active_and_stock_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"{self.url}?is_active=true&stock_status=in_stock"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["external_id"], "EXT-001")

    def test_products_pagination(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?page_size=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["page_size"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_products_ordering(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?ordering=name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, sorted(names))
