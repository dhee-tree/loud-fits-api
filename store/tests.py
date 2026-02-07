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

    def create_store_user(
        self,
        email='store@example.com',
        password='testpass123',
        store_slug='test-store',
        store_name='Test Store',
    ):
        """Create a user with account_type=Store and an associated Store."""
        user = User.objects.create_user(
            email=email,
            password=password,
            account_type=User.AccountType.STORE
        )
        store = Store.objects.create(
            owner=user,
            name=store_name,
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
                    'product_url': 'https://example.com/products/blue-tshirt',
                    'stock_quantity': 15
                },
                {
                    'external_id': 'PROD002',
                    'name': 'Black Jeans',
                    'category': 'bottom',
                    'image_url': 'https://example.com/images/black-jeans.jpg',
                    'price': 59.99,
                    'currency': 'GBP',
                    'product_url': 'https://example.com/products/black-jeans',
                    'stock_quantity': 5
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
        self.assertEqual(response.data['missing_stock_quantity_count'], 0)
        self.assertIsNone(response.data['missing_stock_quantity_message'])

    def test_preview_warns_on_missing_stock_quantity(self):
        """Test preview returns a warning when stock quantity is missing."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Test Product',
                'category': 'top',
                'image_url': 'https://example.com/image.jpg',
                'price': 10.00,
                'currency': 'GBP',
                'product_url': 'https://example.com/product'
            }]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_valid'])
        self.assertEqual(response.data['missing_stock_quantity_count'], 1)
        self.assertIsNotNone(response.data['missing_stock_quantity_message'])

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
        self.assertTrue(response.data['is_valid'])
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
        self.assertEqual(product.stock_quantity, 15)
        self.assertEqual(product.stock_status, StockStatus.IN_STOCK)

        product_two = Product.objects.get(
            store=self.store, external_id='PROD002')
        self.assertEqual(product_two.stock_quantity, 5)
        self.assertEqual(product_two.stock_status, StockStatus.LOW_STOCK)

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
                'product_url': 'https://example.com/products/blue-tshirt',
                'stock_quantity': 3
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
        self.assertEqual(product.stock_quantity, 3)
        self.assertEqual(product.stock_status, StockStatus.LOW_STOCK)

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

    def test_import_rejects_when_no_valid_products(self):
        """Test import fails when there are no valid products."""
        self.client.force_authenticate(user=self.user)

        feed = {
            'products': [{
                'external_id': 'PROD001',
                'name': 'Invalid Product',
                'category': 'invalid_category',
                'image_url': 'not-a-url',
                'price': -1,
                'currency': 'X',
                'product_url': 'also-invalid'
            }]
        }

        response = self.client.post(self.url, feed, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(Product.objects.filter(store=self.store).count(), 0)

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
        external_ids = {item["external_id"]
                        for item in response.data["results"]}
        self.assertSetEqual(external_ids, {"EXT-001", "EXT-002"})
        first_item = response.data["results"][0]
        self.assertIn("uuid", first_item)
        self.assertIn("stock_status", first_item)
        self.assertIn("updated_at", first_item)
        self.assertNotIn("price", first_item)
        self.assertNotIn("currency", first_item)
        self.assertNotIn("product_url", first_item)
        self.assertNotIn("stock_quantity", first_item)
        self.assertNotIn("store", first_item)

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


class StoreProductDetailTests(StoreTestCase):
    """Tests for store product detail endpoints."""

    def setUp(self):
        super().setUp()
        self.user, self.store = self.create_store_user()
        self.other_user, self.other_store = self.create_store_user(
            email="other-store@example.com",
            store_slug="other-store",
            store_name="Other Store",
        )
        self.product = Product.objects.create(
            store=self.store,
            external_id="EXT-001",
            name="Blue Tee",
            category="top",
            image_url="https://example.com/blue.jpg",
            price=19.99,
            currency="GBP",
            product_url="https://example.com/blue",
            is_active=True,
            stock_status=StockStatus.OUT_OF_STOCK,
            stock_quantity=0,
        )
        self.other_product = Product.objects.create(
            store=self.other_store,
            external_id="EXT-002",
            name="Other Tee",
            category="top",
            image_url="https://example.com/other.jpg",
            price=29.99,
            currency="GBP",
            product_url="https://example.com/other",
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=12,
        )
        self.url = f"/api/store/products/{self.product.uuid}/"

    def test_product_detail_requires_authentication(self):
        response = self.client.patch(self.url, {"name": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_detail_requires_store_account(self):
        regular_user = self.create_regular_user()
        self.client.force_authenticate(user=regular_user)
        response = self.client.patch(self.url, {"name": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_product_detail_get_returns_full_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.product.uuid))
        self.assertIn("price", response.data)
        self.assertIn("currency", response.data)
        self.assertIn("product_url", response.data)
        self.assertIn("stock_quantity", response.data)
        self.assertIn("created_at", response.data)
        self.assertIn("store", response.data)

    def test_product_detail_updates_product(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {
                "name": "Updated Tee",
                "price": "24.99",
                "stock_quantity": 4,
                "is_active": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Tee")
        self.assertEqual(float(self.product.price), 24.99)
        self.assertEqual(self.product.stock_quantity, 4)
        self.assertEqual(self.product.stock_status, StockStatus.LOW_STOCK)
        self.assertFalse(self.product.is_active)

    def test_product_detail_blocks_other_store(self):
        self.client.force_authenticate(user=self.user)
        url = f"/api/store/products/{self.other_product.uuid}/"
        response = self.client.patch(url, {"name": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_detail_duplicate_external_id(self):
        Product.objects.create(
            store=self.store,
            external_id="EXT-999",
            name="Another Product",
            category="top",
            image_url="https://example.com/another.jpg",
            price=9.99,
            currency="GBP",
            product_url="https://example.com/another",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"external_id": "EXT-999"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("external_id", response.data)


class StoreManageTests(StoreTestCase):
    """Tests for the store manage endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/api/store/manage/"

    def test_manage_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manage_get_no_store(self):
        user = self.create_regular_user()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["has_store"])
        self.assertIsNone(response.data["store"])

    def test_manage_get_with_store(self):
        user, store = self.create_store_user()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_store"])
        self.assertEqual(response.data["store"]["uuid"], str(store.uuid))

    def test_manage_create_store(self):
        user = self.create_regular_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"name": "Skyline Apparel"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["has_store"])
        self.assertEqual(response.data["store"]["name"], "Skyline Apparel")

        store = Store.objects.get(owner=user)
        self.assertEqual(store.slug, "skyline-apparel")

        user.refresh_from_db()
        self.assertEqual(user.account_type, User.AccountType.STORE)

    def test_manage_create_duplicate_name(self):
        self.create_store_user(store_slug="skyline-apparel",
                               store_name="Skyline Apparel")
        user = self.create_regular_user(email="new@example.com")
        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"name": "Skyline Apparel"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data["details"])

    def test_manage_create_missing_name(self):
        user = self.create_regular_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data["details"])

    def test_manage_create_when_store_exists(self):
        user, _ = self.create_store_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"name": "Another Store"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manage_patch_without_store(self):
        user = self.create_regular_user()
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.url, {"name": "New Name"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manage_patch_updates_store(self):
        user, store = self.create_store_user()
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.url, {"name": "Updated Store"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        store.refresh_from_db()
        self.assertEqual(store.name, "Updated Store")
        self.assertEqual(store.slug, "updated-store")

    def test_manage_patch_duplicate_name(self):
        self.create_store_user(store_slug="skyline-apparel",
                               store_name="Skyline Apparel")
        user, _ = self.create_store_user(
            email="owner@example.com",
            store_slug="owner-store",
            store_name="Owner Store",
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.url, {"name": "Skyline Apparel"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data["details"])


class StoreLastImportTests(StoreTestCase):
    """Tests for the last import endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/api/store/imports/last/"

    def test_last_import_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_last_import_requires_store_account(self):
        user = self.create_regular_user()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_last_import_no_imports(self):
        user, _ = self.create_store_user()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["has_import"])
        self.assertIsNone(response.data["import"])

    def test_last_import_returns_latest(self):
        user, store = self.create_store_user()
        self.client.force_authenticate(user=user)

        ProductImportBatch.objects.create(
            store=store,
            uploaded_by=user,
            total=5,
            imported=5,
            updated=0,
            failed=0,
        )
        latest = ProductImportBatch.objects.create(
            store=store,
            uploaded_by=user,
            total=10,
            imported=8,
            updated=1,
            failed=1,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_import"])
        self.assertEqual(response.data["import"]["batch_id"], str(latest.uuid))
        self.assertEqual(response.data["import"]["failed"], 1)
