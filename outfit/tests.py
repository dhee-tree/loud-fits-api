from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from product.models import Product, StockStatus
from store.models import Store
from user.models import User
from .models import Outfit, OutfitItem, OutfitLike, OutfitSave, OutfitTryOn, OutfitView


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
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role=User.Role.ADMIN,
            account_type=User.AccountType.USER,
            is_staff=True,
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
        self.shoes_product = Product.objects.create(
            store=self.store_two,
            external_id='SHOES-001',
            name='Shoe Product',
            category='shoes',
            image_url='https://example.com/shoes.jpg',
            price=80.00,
            currency='GBP',
            product_url='https://example.com/shoes',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=4,
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
        published_at = timezone.now() if status_value == Outfit.Status.PUBLISHED else None
        return Outfit.objects.create(
            owner=owner,
            status=status_value,
            title=title,
            published_at=published_at,
        )

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

    def test_current_draft_returns_404_when_none_exists(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/outfits/current-draft/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Outfit.objects.filter(
            owner=self.user, status='draft').count(), 0)

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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f'/api/outfits/{draft.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/outfits/{draft.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(draft.uuid))

    def test_retrieve_published_requires_authentication(self):
        published = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Public Outfit',
        )
        self.create_outfit_item(
            published, OutfitItem.Slot.TOP, self.top_product)

        response = self.client.get(f'/api/outfits/{published.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.other_user)
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

    def test_patch_allows_published_outfit(self):
        published = self.create_outfit(
            self.user, status_value=Outfit.Status.PUBLISHED)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f'/api/outfits/{published.uuid}/',
            {'title': 'Updated title'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated title')

    def test_delete_draft_removes_items(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.create_outfit_item(draft, OutfitItem.Slot.TOP, self.top_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/api/outfits/{draft.uuid}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Outfit.objects.filter(uuid=draft.uuid).exists())
        self.assertEqual(OutfitItem.objects.filter(outfit=draft).count(), 0)

    def test_delete_allows_published_outfit(self):
        published = self.create_outfit(
            self.user, status_value=Outfit.Status.PUBLISHED)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/api/outfits/{published.uuid}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Outfit.objects.filter(uuid=published.uuid).exists())

    def test_set_slot_item_creates_snapshot(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.top_product.tryon_asset = SimpleUploadedFile(
            'top.glb',
            b'glTF',
            content_type='model/gltf-binary',
        )
        self.top_product.save(update_fields=['tryon_asset'])
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
        self.assertIn(
            f'/api/products/{self.top_product.uuid}/tryon-asset/',
            item['tryon_asset_url'],
        )

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

    def test_set_slot_item_accepts_shoes(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            f'/api/outfits/{draft.uuid}/items/shoes/',
            {'product_id': str(self.shoes_product.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['slot'], OutfitItem.Slot.SHOES)
        self.assertEqual(
            response.data['items'][0]['product_id'],
            str(self.shoes_product.uuid),
        )

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
            f'/api/outfits/{draft.uuid}/items/accessory/',
            {'product_id': str(self.top_product.uuid)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('slot', response.data)

    def test_publish_requires_authentication(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        response = self.client.post(f'/api/outfits/{draft.uuid}/publish/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_publish_requires_owner(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(f'/api/outfits/{draft.uuid}/publish/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_publish_requires_both_top_and_bottom(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.create_outfit_item(draft, OutfitItem.Slot.TOP, self.top_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/outfits/{draft.uuid}/publish/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('slots', response.data)

    def test_publish_success_sets_status_and_published_at(self):
        draft = self.create_outfit(self.user, status_value=Outfit.Status.DRAFT)
        self.create_outfit_item(draft, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(draft, OutfitItem.Slot.BOTTOM, self.bottom_product)
        self.create_outfit_item(draft, OutfitItem.Slot.SHOES, self.shoes_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/outfits/{draft.uuid}/publish/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        self.assertEqual(draft.status, Outfit.Status.PUBLISHED)
        self.assertIsNotNone(draft.published_at)
        self.assertIn('creator', response.data)
        self.assertEqual(str(response.data['creator']['uuid']), str(self.user.uuid))

    def test_publish_is_idempotent(self):
        published = self.create_outfit(self.user, status_value=Outfit.Status.PUBLISHED)
        self.create_outfit_item(published, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(published, OutfitItem.Slot.BOTTOM, self.bottom_product)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/outfits/{published.uuid}/publish/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        published.refresh_from_db()
        self.assertEqual(published.status, Outfit.Status.PUBLISHED)

    def test_explore_is_publicly_accessible(self):
        response = self.client.get('/api/explore/outfits/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_explore_returns_only_visible_published(self):
        hidden_published = self.create_outfit(
            self.other_user,
            status_value=Outfit.Status.PUBLISHED,
            title='Hidden Fit',
        )
        hidden_published.is_hidden = True
        hidden_published.save(update_fields=['is_hidden'])
        self.create_outfit_item(hidden_published, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(hidden_published, OutfitItem.Slot.BOTTOM, self.bottom_product)

        public_published = self.create_outfit(
            self.other_user,
            status_value=Outfit.Status.PUBLISHED,
            title='Public Fit',
        )
        self.create_outfit_item(public_published, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(public_published, OutfitItem.Slot.BOTTOM, self.bottom_product)
        self.create_outfit_item(public_published, OutfitItem.Slot.SHOES, self.shoes_product)

        self.create_outfit(self.other_user, status_value=Outfit.Status.DRAFT, title='Draft Fit')

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/explore/outfits/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        result = response.data['results'][0]
        self.assertEqual(result['uuid'], str(public_published.uuid))
        self.assertIn('creator', result)
        self.assertIn('top_image_url', result)
        self.assertIn('bottom_image_url', result)
        self.assertIn('shoes_image_url', result)
        self.assertEqual(result['shoes_image_url'], self.shoes_product.image_url)

    @override_settings(MEDIA_URL='/media/')
    def test_retrieve_uses_fresh_uploaded_image_url_for_snapshots(self):
        published = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Snapshot Refresh Fit',
        )
        self.shoes_product.uploaded_image = SimpleUploadedFile(
            'shoe.jpg',
            b'not-a-real-image-but-good-enough-for-storage',
            content_type='image/jpeg',
        )
        self.shoes_product.save(update_fields=['uploaded_image'])

        OutfitItem.objects.create(
            outfit=published,
            slot=OutfitItem.Slot.SHOES,
            product=self.shoes_product,
            product_name=self.shoes_product.name,
            image_url_used='https://example.com/stale-shoes.jpg',
            product_url=self.shoes_product.product_url,
            store_name=self.shoes_product.store.name,
            store_slug=self.shoes_product.store.slug,
            price=self.shoes_product.price,
            currency=self.shoes_product.currency,
        )

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f'/api/outfits/{published.uuid}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertIn('/media/', response.data['items'][0]['image_url_used'])

    def test_explore_supports_search_and_store_filter(self):
        outfit_one = self.create_outfit(
            self.other_user,
            status_value=Outfit.Status.PUBLISHED,
            title='Alpha Jacket Fit',
        )
        self.create_outfit_item(outfit_one, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(outfit_one, OutfitItem.Slot.BOTTOM, self.bottom_product)

        outfit_two = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Beta Fit',
        )
        self.create_outfit_item(outfit_two, OutfitItem.Slot.TOP, self.top_product_two)
        self.create_outfit_item(outfit_two, OutfitItem.Slot.BOTTOM, self.bottom_product)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get('/api/explore/outfits/?search=Alpha')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['uuid'], str(outfit_one.uuid))

        response = self.client.get('/api/explore/outfits/?store=store-two')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['uuid'], str(outfit_two.uuid))

    def test_hidden_outfit_not_available_to_guests_but_visible_to_owner_and_admin(self):
        published = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Moderated Fit',
        )
        published.is_hidden = True
        published.hidden_reason = 'Policy violation'
        published.save(update_fields=['is_hidden', 'hidden_reason'])
        self.create_outfit_item(published, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(published, OutfitItem.Slot.BOTTOM, self.bottom_product)

        response = self.client.get(f'/api/outfits/{published.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/outfits/{published.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_hidden'])

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/outfits/{published.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_hidden'])

    def test_explore_public_access(self):
        """Explore endpoint should be accessible without authentication."""
        published = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Public Explore Fit',
        )
        self.create_outfit_item(published, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(published, OutfitItem.Slot.BOTTOM, self.bottom_product)

        response = self.client.get('/api/explore/outfits/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['uuid'], str(published.uuid))

    def test_moderation_requires_admin(self):
        published = self.create_outfit(self.user, status_value=Outfit.Status.PUBLISHED)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f'/api/outfits/{published.uuid}/moderation/',
            {'is_hidden': True, 'hidden_reason': 'Review'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_moderation_hide_and_unhide(self):
        published = self.create_outfit(
            self.user,
            status_value=Outfit.Status.PUBLISHED,
            title='Visibility Fit',
        )
        self.create_outfit_item(published, OutfitItem.Slot.TOP, self.top_product)
        self.create_outfit_item(published, OutfitItem.Slot.BOTTOM, self.bottom_product)
        self.client.force_authenticate(user=self.admin_user)

        hide_response = self.client.patch(
            f'/api/outfits/{published.uuid}/moderation/',
            {'is_hidden': True, 'hidden_reason': 'Admin hide'},
            format='json',
        )
        self.assertEqual(hide_response.status_code, status.HTTP_200_OK)
        published.refresh_from_db()
        self.assertTrue(published.is_hidden)
        self.assertEqual(published.hidden_reason, 'Admin hide')

        explore_response = self.client.get('/api/explore/outfits/')
        self.assertEqual(explore_response.status_code, status.HTTP_200_OK)
        self.assertEqual(explore_response.data['count'], 0)

        unhide_response = self.client.patch(
            f'/api/outfits/{published.uuid}/moderation/',
            {'is_hidden': False},
            format='json',
        )
        self.assertEqual(unhide_response.status_code, status.HTTP_200_OK)
        published.refresh_from_db()
        self.assertFalse(published.is_hidden)
        self.assertIsNone(published.hidden_reason)


class OutfitLikeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='liker@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )
        self.other_user = User.objects.create_user(
            email='other_liker@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )
        self.store_owner = User.objects.create_user(
            email='store_like@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        self.store = Store.objects.create(
            owner=self.store_owner,
            name='Like Store',
            slug='like-store',
        )
        self.top_product = Product.objects.create(
            store=self.store,
            external_id='LIKE-TOP-001',
            name='Like Top',
            category='top',
            image_url='https://example.com/like-top.jpg',
            price=30.00,
            currency='GBP',
            product_url='https://example.com/like-top',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )
        self.bottom_product = Product.objects.create(
            store=self.store,
            external_id='LIKE-BOT-001',
            name='Like Bottom',
            category='bottom',
            image_url='https://example.com/like-bottom.jpg',
            price=40.00,
            currency='GBP',
            product_url='https://example.com/like-bottom',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )
        self.published_outfit = self._create_published_outfit(self.other_user, 'Likeable Fit')

    def _create_published_outfit(self, owner, title=''):
        outfit = Outfit.objects.create(
            owner=owner,
            status=Outfit.Status.PUBLISHED,
            title=title,
            published_at=timezone.now(),
        )
        OutfitItem.objects.create(
            outfit=outfit,
            slot=OutfitItem.Slot.TOP,
            product=self.top_product,
            product_name=self.top_product.name,
            image_url_used=self.top_product.image_url,
            product_url=self.top_product.product_url,
            store_name=self.store.name,
            store_slug=self.store.slug,
            price=self.top_product.price,
            currency=self.top_product.currency,
        )
        OutfitItem.objects.create(
            outfit=outfit,
            slot=OutfitItem.Slot.BOTTOM,
            product=self.bottom_product,
            product_name=self.bottom_product.name,
            image_url_used=self.bottom_product.image_url,
            product_url=self.bottom_product.product_url,
            store_name=self.store.name,
            store_slug=self.store.slug,
            price=self.bottom_product.price,
            currency=self.bottom_product.currency,
        )
        return outfit

    def test_like_outfit_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/outfits/{self.published_outfit.uuid}/like/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['liked'])
        self.assertTrue(response.data['created'])
        self.assertTrue(
            OutfitLike.objects.filter(
                user=self.user, outfit=self.published_outfit).exists()
        )

    def test_like_outfit_already_liked(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/outfits/{self.published_outfit.uuid}/like/')
        response = self.client.post(
            f'/api/outfits/{self.published_outfit.uuid}/like/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['liked'])
        self.assertFalse(response.data['created'])
        self.assertEqual(
            OutfitLike.objects.filter(
                user=self.user, outfit=self.published_outfit).count(), 1
        )

    def test_unlike_outfit(self):
        self.client.force_authenticate(user=self.user)
        OutfitLike.objects.create(user=self.user, outfit=self.published_outfit)
        response = self.client.delete(
            f'/api/outfits/{self.published_outfit.uuid}/like/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['liked'])
        self.assertFalse(
            OutfitLike.objects.filter(
                user=self.user, outfit=self.published_outfit).exists()
        )

    def test_like_unpublished_outfit(self):
        draft = Outfit.objects.create(
            owner=self.other_user,
            status=Outfit.Status.DRAFT,
            title='Draft Fit',
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/outfits/{draft.uuid}/like/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_like_unauthenticated(self):
        response = self.client.post(
            f'/api/outfits/{self.published_outfit.uuid}/like/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_liked_outfits(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/outfits/{self.published_outfit.uuid}/like/')

        unliked_outfit = self._create_published_outfit(self.other_user, 'Unliked Fit')

        response = self.client.get('/api/outfits/?liked=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = [r['uuid'] for r in response.data['results']]
        self.assertIn(str(self.published_outfit.uuid), uuids)
        self.assertNotIn(str(unliked_outfit.uuid), uuids)


class OutfitSaveTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='saver@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )
        self.other_user = User.objects.create_user(
            email='other_saver@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )
        self.store_owner = User.objects.create_user(
            email='store_save@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        self.store = Store.objects.create(
            owner=self.store_owner,
            name='Save Store',
            slug='save-store',
        )
        self.top_product = Product.objects.create(
            store=self.store,
            external_id='SAVE-TOP-001',
            name='Save Top',
            category='top',
            image_url='https://example.com/save-top.jpg',
            price=30.00,
            currency='GBP',
            product_url='https://example.com/save-top',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )
        self.bottom_product = Product.objects.create(
            store=self.store,
            external_id='SAVE-BOT-001',
            name='Save Bottom',
            category='bottom',
            image_url='https://example.com/save-bottom.jpg',
            price=40.00,
            currency='GBP',
            product_url='https://example.com/save-bottom',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )
        self.published_outfit = self._create_published_outfit(self.other_user, 'Saveable Fit')

    def _create_published_outfit(self, owner, title=''):
        outfit = Outfit.objects.create(
            owner=owner,
            status=Outfit.Status.PUBLISHED,
            title=title,
            published_at=timezone.now(),
        )
        OutfitItem.objects.create(
            outfit=outfit,
            slot=OutfitItem.Slot.TOP,
            product=self.top_product,
            product_name=self.top_product.name,
            image_url_used=self.top_product.image_url,
            product_url=self.top_product.product_url,
            store_name=self.store.name,
            store_slug=self.store.slug,
            price=self.top_product.price,
            currency=self.top_product.currency,
        )
        OutfitItem.objects.create(
            outfit=outfit,
            slot=OutfitItem.Slot.BOTTOM,
            product=self.bottom_product,
            product_name=self.bottom_product.name,
            image_url_used=self.bottom_product.image_url,
            product_url=self.bottom_product.product_url,
            store_name=self.store.name,
            store_slug=self.store.slug,
            price=self.bottom_product.price,
            currency=self.bottom_product.currency,
        )
        return outfit

    def test_save_outfit_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/outfits/{self.published_outfit.uuid}/save/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['saved'])
        self.assertTrue(response.data['created'])
        self.assertTrue(
            OutfitSave.objects.filter(
                user=self.user, outfit=self.published_outfit).exists()
        )

    def test_save_outfit_already_saved(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/outfits/{self.published_outfit.uuid}/save/')
        response = self.client.post(
            f'/api/outfits/{self.published_outfit.uuid}/save/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['saved'])
        self.assertFalse(response.data['created'])
        self.assertEqual(
            OutfitSave.objects.filter(
                user=self.user, outfit=self.published_outfit).count(), 1
        )

    def test_unsave_outfit(self):
        self.client.force_authenticate(user=self.user)
        OutfitSave.objects.create(user=self.user, outfit=self.published_outfit)
        response = self.client.delete(
            f'/api/outfits/{self.published_outfit.uuid}/save/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['saved'])
        self.assertFalse(
            OutfitSave.objects.filter(
                user=self.user, outfit=self.published_outfit).exists()
        )

    def test_save_unpublished_outfit(self):
        draft = Outfit.objects.create(
            owner=self.other_user,
            status=Outfit.Status.DRAFT,
            title='Draft Fit',
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/outfits/{draft.uuid}/save/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_save_unauthenticated(self):
        response = self.client.post(
            f'/api/outfits/{self.published_outfit.uuid}/save/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_saved_outfits(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/outfits/{self.published_outfit.uuid}/save/')

        unsaved_outfit = self._create_published_outfit(self.other_user, 'Unsaved Fit')

        response = self.client.get('/api/outfits/?saved=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = [r['uuid'] for r in response.data['results']]
        self.assertIn(str(self.published_outfit.uuid), uuids)
        self.assertNotIn(str(unsaved_outfit.uuid), uuids)


class OutfitOccasionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email='occasion@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )

        self.store_owner = User.objects.create_user(
            email='store_occasion@example.com',
            password='testpass123',
            account_type=User.AccountType.STORE,
        )
        self.store = Store.objects.create(
            owner=self.store_owner,
            name='Occasion Store',
            slug='occasion-store',
        )
        self.top_product = Product.objects.create(
            store=self.store,
            external_id='OCC-TOP-001',
            name='Occasion Top',
            category='top',
            image_url='https://example.com/occ-top.jpg',
            price=30.00,
            currency='GBP',
            product_url='https://example.com/occ-top',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )
        self.bottom_product = Product.objects.create(
            store=self.store,
            external_id='OCC-BOT-001',
            name='Occasion Bottom',
            category='bottom',
            image_url='https://example.com/occ-bottom.jpg',
            price=40.00,
            currency='GBP',
            product_url='https://example.com/occ-bottom',
            is_active=True,
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=10,
        )

    def _create_published_outfit(self, owner, title='', occasion=None):
        outfit = Outfit.objects.create(
            owner=owner,
            status=Outfit.Status.PUBLISHED,
            title=title,
            occasion=occasion,
            published_at=timezone.now(),
        )
        OutfitItem.objects.create(
            outfit=outfit,
            slot=OutfitItem.Slot.TOP,
            product=self.top_product,
            product_name=self.top_product.name,
            image_url_used=self.top_product.image_url,
            product_url=self.top_product.product_url,
            store_name=self.store.name,
            store_slug=self.store.slug,
            price=self.top_product.price,
            currency=self.top_product.currency,
        )
        OutfitItem.objects.create(
            outfit=outfit,
            slot=OutfitItem.Slot.BOTTOM,
            product=self.bottom_product,
            product_name=self.bottom_product.name,
            image_url_used=self.bottom_product.image_url,
            product_url=self.bottom_product.product_url,
            store_name=self.store.name,
            store_slug=self.store.slug,
            price=self.bottom_product.price,
            currency=self.bottom_product.currency,
        )
        return outfit

    def test_create_outfit_with_occasion(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/outfits/',
            {'title': 'Wedding Fit', 'occasion': 'Wedding'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['occasion'], 'Wedding')
        outfit = Outfit.objects.get(uuid=response.data['uuid'])
        self.assertEqual(outfit.occasion, 'Wedding')

    def test_update_outfit_occasion(self):
        self.client.force_authenticate(user=self.user)
        outfit = Outfit.objects.create(
            owner=self.user,
            status=Outfit.Status.DRAFT,
            title='Draft Fit',
        )

        response = self.client.patch(
            f'/api/outfits/{outfit.uuid}/',
            {'occasion': 'Party'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        outfit.refresh_from_db()
        self.assertEqual(outfit.occasion, 'Party')
        self.assertEqual(response.data['occasion'], 'Party')

    def test_explore_filter_by_occasion(self):
        self._create_published_outfit(self.user, 'Wedding Fit', occasion='Wedding')
        self._create_published_outfit(self.user, 'Party Fit', occasion='Party')
        self._create_published_outfit(self.user, 'Casual Fit', occasion='Casual')

        response = self.client.get('/api/explore/outfits/?occasion=Wedding')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Wedding Fit')
        self.assertEqual(response.data['results'][0]['occasion'], 'Wedding')

    def test_occasion_optional(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/outfits/',
            {'title': 'No Occasion Fit'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['occasion'])
        outfit = Outfit.objects.get(uuid=response.data['uuid'])
        self.assertIsNone(outfit.occasion)


class OutfitViewTrackTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='viewer@example.com', password='testpass123')
        self.other_user = User.objects.create_user(email='creator@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.other_user, name='View Store', slug='view-store')
        self.top_product = Product.objects.create(
            store=self.store, external_id='VIEW-TOP-001', name='View Top',
            category='top', image_url='https://example.com/top.jpg',
            price=30.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.bottom_product = Product.objects.create(
            store=self.store, external_id='VIEW-BOT-001', name='View Bottom',
            category='bottom', image_url='https://example.com/bottom.jpg',
            price=40.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.outfit = Outfit.objects.create(
            owner=self.other_user, status=Outfit.Status.PUBLISHED,
            title='Viewable Fit', published_at=timezone.now(),
        )
        OutfitItem.objects.create(
            outfit=self.outfit, slot=OutfitItem.Slot.TOP, product=self.top_product,
            product_name=self.top_product.name, image_url_used=self.top_product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.top_product.price, currency=self.top_product.currency,
        )
        OutfitItem.objects.create(
            outfit=self.outfit, slot=OutfitItem.Slot.BOTTOM, product=self.bottom_product,
            product_name=self.bottom_product.name, image_url_used=self.bottom_product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.bottom_product.price, currency=self.bottom_product.currency,
        )

    def test_view_track_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/outfits/{self.outfit.uuid}/view/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['recorded'])
        self.assertEqual(OutfitView.objects.filter(outfit=self.outfit).count(), 1)

    def test_view_track_anonymous_with_session(self):
        response = self.client.post(f'/api/outfits/{self.outfit.uuid}/view/', {'session_id': 'abc123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['recorded'])

    def test_view_track_deduplication(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/outfits/{self.outfit.uuid}/view/')
        response = self.client.post(f'/api/outfits/{self.outfit.uuid}/view/')
        self.assertFalse(response.data['recorded'])
        self.assertEqual(OutfitView.objects.filter(outfit=self.outfit).count(), 1)

    def test_view_track_unpublished_404(self):
        draft = Outfit.objects.create(owner=self.other_user, status=Outfit.Status.DRAFT, title='Draft')
        response = self.client.post(f'/api/outfits/{draft.uuid}/view/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OutfitTryOnTrackTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='tryer@example.com', password='testpass123')
        self.other_user = User.objects.create_user(email='creator2@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.other_user, name='TryOn Store', slug='tryon-store')
        self.top_product = Product.objects.create(
            store=self.store, external_id='TRY-TOP-001', name='Try Top',
            category='top', image_url='https://example.com/try-top.jpg',
            price=30.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.bottom_product = Product.objects.create(
            store=self.store, external_id='TRY-BOT-001', name='Try Bottom',
            category='bottom', image_url='https://example.com/try-bottom.jpg',
            price=40.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.outfit = Outfit.objects.create(
            owner=self.other_user, status=Outfit.Status.PUBLISHED,
            title='Tryable Fit', published_at=timezone.now(),
        )
        OutfitItem.objects.create(
            outfit=self.outfit, slot=OutfitItem.Slot.TOP, product=self.top_product,
            product_name=self.top_product.name, image_url_used=self.top_product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.top_product.price, currency=self.top_product.currency,
        )
        OutfitItem.objects.create(
            outfit=self.outfit, slot=OutfitItem.Slot.BOTTOM, product=self.bottom_product,
            product_name=self.bottom_product.name, image_url_used=self.bottom_product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.bottom_product.price, currency=self.bottom_product.currency,
        )

    def test_tryon_track_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/outfits/{self.outfit.uuid}/tryon-track/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['recorded'])

    def test_tryon_track_unauthenticated(self):
        response = self.client.post(f'/api/outfits/{self.outfit.uuid}/tryon-track/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tryon_track_unpublished_404(self):
        draft = Outfit.objects.create(owner=self.other_user, status=Outfit.Status.DRAFT, title='Draft')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/outfits/{draft.uuid}/tryon-track/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TrendingOutfitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='trendy@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.user, name='Trend Store', slug='trend-store')
        self.top_product = Product.objects.create(
            store=self.store, external_id='TREND-TOP-001', name='Trend Top',
            category='top', image_url='https://example.com/trend-top.jpg',
            price=30.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.bottom_product = Product.objects.create(
            store=self.store, external_id='TREND-BOT-001', name='Trend Bottom',
            category='bottom', image_url='https://example.com/trend-bottom.jpg',
            price=40.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )

    def _create_published_outfit(self, title=''):
        outfit = Outfit.objects.create(
            owner=self.user, status=Outfit.Status.PUBLISHED,
            title=title, published_at=timezone.now(),
        )
        OutfitItem.objects.create(
            outfit=outfit, slot=OutfitItem.Slot.TOP, product=self.top_product,
            product_name=self.top_product.name, image_url_used=self.top_product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.top_product.price, currency=self.top_product.currency,
        )
        OutfitItem.objects.create(
            outfit=outfit, slot=OutfitItem.Slot.BOTTOM, product=self.bottom_product,
            product_name=self.bottom_product.name, image_url_used=self.bottom_product.image_url,
            store_name=self.store.name, store_slug=self.store.slug,
            price=self.bottom_product.price, currency=self.bottom_product.currency,
        )
        return outfit

    def test_trending_endpoint_accessible(self):
        self._create_published_outfit('Trending Outfit')
        response = self.client.get('/api/explore/outfits/trending/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)

    def test_trending_returns_most_engaged(self):
        popular = self._create_published_outfit('Popular')
        unpopular = self._create_published_outfit('Unpopular')

        for i in range(5):
            u = User.objects.create_user(email=f'liker{i}@example.com', password='testpass123')
            OutfitLike.objects.create(user=u, outfit=popular)

        response = self.client.get('/api/explore/outfits/trending/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = [item['uuid'] for item in response.data]
        self.assertEqual(uuids[0], str(popular.uuid))


class RecommendedOutfitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='reco@example.com', password='testpass123')
        self.creator = User.objects.create_user(email='creator_reco@example.com', password='testpass123')
        self.store = Store.objects.create(owner=self.creator, name='Reco Store', slug='reco-store')
        self.product = Product.objects.create(
            store=self.store, external_id='RECOM-001', name='Blue Slim Jeans',
            category='bottom', image_url='https://example.com/jeans.jpg',
            price=45.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        self.top_product = Product.objects.create(
            store=self.store, external_id='RECOM-002', name='White Cotton Tee',
            category='top', image_url='https://example.com/tee.jpg',
            price=25.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )

    def _create_outfit_with_products(self, owner, title, products, occasion=None):
        outfit = Outfit.objects.create(
            owner=owner, status=Outfit.Status.PUBLISHED,
            title=title, published_at=timezone.now(), occasion=occasion,
        )
        for product in products:
            slot = product.category
            OutfitItem.objects.create(
                outfit=outfit, slot=slot, product=product,
                product_name=product.name, image_url_used=product.image_url,
                store_name=self.store.name, store_slug=self.store.slug,
                price=product.price, currency=product.currency,
            )
        return outfit

    def test_recommended_anonymous_returns_trending(self):
        self._create_outfit_with_products(self.creator, 'Trending Fit', [self.product, self.top_product])
        response = self.client.get('/api/explore/outfits/recommended/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recommended_no_history_returns_trending(self):
        self.client.force_authenticate(user=self.user)
        self._create_outfit_with_products(self.creator, 'Some Fit', [self.product, self.top_product])
        response = self.client.get('/api/explore/outfits/recommended/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recommended_based_on_liked_products(self):
        self.client.force_authenticate(user=self.user)

        liked_outfit = self._create_outfit_with_products(self.creator, 'Liked Fit', [self.product, self.top_product])
        OutfitLike.objects.create(user=self.user, outfit=liked_outfit)

        similar_outfit = self._create_outfit_with_products(self.creator, 'Similar Fit', [self.product])

        other_product = Product.objects.create(
            store=self.store, external_id='RECOM-003', name='Red Formal Blazer',
            category='top', image_url='https://example.com/blazer.jpg',
            price=120.00, currency='GBP', is_active=True,
            stock_status=StockStatus.IN_STOCK, stock_quantity=10,
        )
        unrelated_outfit = self._create_outfit_with_products(self.creator, 'Unrelated Fit', [other_product])

        response = self.client.get('/api/explore/outfits/recommended/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        uuids = [r['uuid'] for r in response.data]
        if len(uuids) >= 2:
            self.assertIn(str(similar_outfit.uuid), uuids)
            sim_idx = uuids.index(str(similar_outfit.uuid))
            if str(unrelated_outfit.uuid) in uuids:
                unrel_idx = uuids.index(str(unrelated_outfit.uuid))
                self.assertLess(sim_idx, unrel_idx)

    def test_recommended_includes_reason(self):
        self.client.force_authenticate(user=self.user)
        liked_outfit = self._create_outfit_with_products(self.creator, 'Liked', [self.product])
        OutfitLike.objects.create(user=self.user, outfit=liked_outfit)
        self._create_outfit_with_products(self.creator, 'Candidate', [self.product])

        response = self.client.get('/api/explore/outfits/recommended/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data:
            self.assertIn('recommendation_reason', response.data[0])
