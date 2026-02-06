from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from store.models import Store
from .models import Product, StockStatus


class ProductBrowseTests(TestCase):
    """Tests for the public product browse endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/products/"

        owner_one = User.objects.create_user(
            email="owner1@example.com",
            password="testpass123",
            account_type=User.AccountType.STORE,
        )
        owner_two = User.objects.create_user(
            email="owner2@example.com",
            password="testpass123",
            account_type=User.AccountType.STORE,
        )

        self.store_one = Store.objects.create(
            owner=owner_one, name="Store One", slug="store-one"
        )
        self.store_two = Store.objects.create(
            owner=owner_two, name="Store Two", slug="store-two"
        )

        Product.objects.create(
            store=self.store_one,
            external_id="P-001",
            name="Blue Tee",
            category="top",
            image_url="https://example.com/blue.jpg",
            price=19.99,
            currency="GBP",
            product_url="https://example.com/blue",
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=12,
        )
        Product.objects.create(
            store=self.store_one,
            external_id="P-002",
            name="Grey Hoodie",
            category="top",
            image_url="https://example.com/grey.jpg",
            price=49.99,
            currency="GBP",
            product_url="https://example.com/grey",
            is_active=True,
            stock_status=StockStatus.LOW_STOCK,
            stock_quantity=3,
        )
        Product.objects.create(
            store=self.store_one,
            external_id="P-003",
            name="Black Jeans",
            category="bottom",
            image_url="https://example.com/black.jpg",
            price=59.99,
            currency="GBP",
            product_url="https://example.com/black",
            is_active=True,
            stock_status=StockStatus.OUT_OF_STOCK,
            stock_quantity=0,
        )
        Product.objects.create(
            store=self.store_one,
            external_id="P-004",
            name="Inactive Tee",
            category="top",
            image_url="https://example.com/inactive.jpg",
            price=9.99,
            currency="GBP",
            product_url="https://example.com/inactive",
            is_active=False,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=20,
        )
        Product.objects.create(
            store=self.store_two,
            external_id="P-005",
            name="White Trainers",
            category="bottom",
            image_url="https://example.com/trainers.jpg",
            price=89.99,
            currency="GBP",
            product_url="https://example.com/trainers",
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=6,
        )

    def test_default_filters_exclude_out_of_stock_and_inactive(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        external_ids = {item["external_id"] for item in response.data["results"]}
        self.assertSetEqual(external_ids, {"P-001", "P-002", "P-005"})

    def test_override_is_active_filter(self):
        response = self.client.get(f"{self.url}?is_active=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["external_id"], "P-004")

    def test_override_stock_status_filter(self):
        response = self.client.get(f"{self.url}?stock_status=out_of_stock")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["external_id"], "P-003")

    def test_filter_by_store_slugs(self):
        response = self.client.get(f"{self.url}?stores=store-one")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        external_ids = {item["external_id"] for item in response.data["results"]}
        self.assertSetEqual(external_ids, {"P-001", "P-002"})

    def test_filter_by_category(self):
        response = self.client.get(f"{self.url}?category=bottom")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        external_ids = {item["external_id"] for item in response.data["results"]}
        self.assertSetEqual(external_ids, {"P-005"})

    def test_search_by_name(self):
        response = self.client.get(f"{self.url}?search=Blue")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["external_id"], "P-001")

    def test_pagination_page_size(self):
        response = self.client.get(f"{self.url}?page_size=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["page_size"], 1)
        self.assertEqual(len(response.data["results"]), 1)
