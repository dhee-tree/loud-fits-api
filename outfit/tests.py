from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from product.models import Product, StockStatus
from store.models import Store
from user.models import User
from .models import Outfit, OutfitItem


class OutfitApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )

        self.store_owner_one = User.objects.create_user(
            email='store1@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        self.store_owner_two = User.objects.create_user(
            email='store2@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        self.store_one = Store.objects.create(
            owner=self.store_owner_one,
            name='Store One',
            slug='store-one',
        )
        self.store_two = Store.objects.create(
            owner=self.store_owner_two,
            name='Store Two',
            slug='store-two',
        )

        self.top_product = Product.objects.create(
            store=self.store_one,
            external_id='TOP-001',
            name='Top Product',
            category='top',
            image_url='https://example.com/top.jpg',
            price=25.50,
            currency='GBP',
            product_url='https://example.com/top',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )
        self.top_product_two = Product.objects.create(
            store=self.store_two,
            external_id='TOP-002',
            name='Second Top',
            category='top',
            image_url='https://example.com/top-2.jpg',
            price=35.00,
            currency='GBP',
            product_url='https://example.com/top-2',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=8,
        )
        self.bottom_product = Product.objects.create(
            store=self.store_one,
            external_id='BOTTOM-001',
            name='Bottom Product',
            category='bottom',
            image_url='https://example.com/bottom.jpg',
            price=55.00,
            currency='GBP',
            product_url='https://example.com/bottom',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=6,
        )
        self.inactive_product = Product.objects.create(
            store=self.store_one,
            external_id='TOP-003',
            name='Inactive Top',
            category='top',
            image_url='https://example.com/inactive.jpg',
            price=20.00,
            currency='GBP',
            product_url='https://example.com/inactive',
            is_active=False,
            stock_status=StockStatus.OUT_OF_STOCK,
            stock_quantity=0,
        )

    @staticmethod
    def create_outfit(owner, status_value=Outfit.Status.DRAFT, title=''):
        return Outfit.objects.create(owner=owner, status=status_value, title=title)

    @staticmethod
    def create_outfit_item(outfit, slot, product):
        item = OutfitItem.objects.create(
            outfit=outfit,
            slot=slot,
            product=product,
            product_name=product.name,
            image_url_used=product.image_url,
            product_url=product.product_url,
            store_name=product.store.name,
            store_slug=product.store.slug,
            price=product.price,
            currency=product.currency,
        )
        return item

    def test_current_draft_requires_authentication(self):
        response = self.client.get('/api/outfits/current-draft/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_draft_creates_new_when_none_exists(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/outfits/current-draft/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Outfit.Status.DRAFT)
        self.assertEqual(Outfit.objects.filter(
            owner=self.user, status='draft').count(), 1)

    def test_current_draft_returns_latest_existing_draft(self):
        first = self.create_outfit(self.user, title='Old Draft')
        latest = self.create_outfit(self.user, title='Latest Draft')
        latest.save(update_fields=['updated_at'])

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/outfits/current-draft/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(latest.uuid))
        self.assertNotEqual(str(first.uuid), response.data['uuid'])

    def test_create_outfit_creates_draft(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/outfits/',
            {'title': 'My Fit', 'notes': 'A simple note'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Outfit.Status.DRAFT)
        self.assertEqual(response.data['title'], 'My Fit')
        self.assertEqual(response.data['notes'], 'A simple note')

    def test_list_drafts_filters_to_owner(self):
        self.create_outfit(
            self.user, status_value=Outfit.Status.DRAFT, title='Mine')
        self.create_outfit(
            self.other_user, status_value=Outfit.Status.DRAFT, title='Not Mine')
        self.create_outfit(
            self.user, status_value=Outfit.Status.PUBLISHED, title='Published')

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/outfits/?status=draft')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mine')

    def test_list_published_with_mine_true(self):
        self.create_outfit(
            self.user, status_value=Outfit.Status.PUBLISHED, title='Mine Published')
        self.create_outfit(
            self.other_user, status_value=Outfit.Status.PUBLISHED, title='Other Published')
        self.create_outfit(
            self.user, status_value=Outfit.Status.DRAFT, title='Mine Draft')

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/outfits/?status=published&mine=true')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results']
                         [0]['title'], 'Mine Published')

    def test_retrieve_draft_is_owner_only(self):
        draft = self.create_outfit(
            self.user, status_value=Outfit.Status.DRAFT, title='Private Draft')

        response = self.client.get(f'/api/outfits/{draft.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f'/api/outfits/{draft.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/outfits/{draft.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(draft.uuid))

    def test_retrieve_published_is_public(self):
        published = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Public Outfit',
        )
        self.create_outfit_item(
            published, OutfitItem.Slot.TOP, self.top_product)

        response = self.client.get(f'/api/outfits/{published.uuid}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(published.uuid))
        self.assertEqual(len(response.data['items']), 1)

    def test_patch_updates_draft_metadata(self):
        draft = self.create_outfit(
            self.user, status_value=Outfit.Status.DRAFT, title='Original')
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f'/api/outfits/{draft.uuid}/',
            {'title': 'Updated', 'notes': 'Updated note'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        self.assertEqual(draft.title, 'Updated')
        self.assertEqual(draft.notes, 'Updated note')

    def test_patch_rejects_published_outfit(self):
        published = self.create_outfit(
            self.user, status_value=Outfit.Status.PUBLISHED)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f'/api/outfits/{published.uuid}/',
            {'title': 'Should fail'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_delete_draft_removes_items(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.create_outfit_item(draft, OutfitItem.Slot.TOP, self.top_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/api/outfits/{draft.uuid}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Outfit.objects.filter(uuid=draft.uuid).exists())
        self.assertEqual(OutfitItem.objects.filter(outfit=draft).count(), 0)

    def test_delete_rejects_published_outfit(self):
        published = self.create_outfit(
            self.user, status_value=Outfit.Status.PUBLISHED)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/api/outfits/{published.uuid}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Outfit.objects.filter(uuid=published.uuid).exists())

    def test_set_slot_item_creates_snapshot(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            f'/api/outfits/{draft.uuid}/items/top/',
            {'product_id': str(self.top_product.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        item = response.data['items'][0]
        self.assertEqual(item['slot'], OutfitItem.Slot.TOP)
        self.assertEqual(item['product_id'], str(self.top_product.uuid))
        self.assertEqual(item['product_name'], self.top_product.name)
        self.assertEqual(item['image_url_used'], self.top_product.image_url)
        self.assertEqual(item['store_name'], self.store_one.name)
        self.assertEqual(item['store_slug'], self.store_one.slug)
        self.assertEqual(item['currency'], self.top_product.currency)

    def test_set_slot_item_replaces_existing(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.create_outfit_item(draft, OutfitItem.Slot.TOP, self.top_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            f'/api/outfits/{draft.uuid}/items/top/',
            {'product_id': str(self.top_product_two.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OutfitItem.objects.filter(
            outfit=draft, slot='top').count(), 1)
        item = OutfitItem.objects.get(outfit=draft, slot='top')
        self.assertEqual(item.product_id, self.top_product_two.uuid)
        self.assertEqual(item.store_slug, self.store_two.slug)

    def test_set_slot_item_rejects_inactive_product(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            f'/api/outfits/{draft.uuid}/items/top/',
            {'product_id': str(self.inactive_product.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('product_id', response.data)

    def test_set_slot_item_rejects_category_mismatch(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            f'/api/outfits/{draft.uuid}/items/top/',
            {'product_id': str(self.bottom_product.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('product_id', response.data)

    def test_delete_slot_item(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.create_outfit_item(
            draft, OutfitItem.Slot.BOTTOM, self.bottom_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            f'/api/outfits/{draft.uuid}/items/bottom/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            OutfitItem.objects.filter(
                outfit=draft, slot=OutfitItem.Slot.BOTTOM).exists()
        )

    def test_slot_endpoint_rejects_invalid_slot(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            f'/api/outfits/{draft.uuid}/items/shoes/',
            {'product_id': str(self.top_product.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('slot', response.data)
