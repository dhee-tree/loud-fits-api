from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from .models import Profile, CreatorFollow


class ProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/profile/'
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User'
        )

    def test_get_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('uuid', response.data)
        self.assertIn('shopping_preference', response.data)
        self.assertIn('avatar_size', response.data)
        self.assertIn('stylist_enabled', response.data)
        self.assertEqual(response.data['stylist_enabled'], False)

    def test_get_profile_unauthenticated(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile_update_shopping_preference(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'shopping_preference': 'Menswear'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['shopping_preference'], 'Menswear')

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.shopping_preference, 'Menswear')

    def test_patch_profile_enable_stylist(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'stylist_enabled': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stylist_enabled'], True)

    def test_patch_profile_invalid_shopping_preference(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'shopping_preference': 'INVALID'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CreatorProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = User.objects.create_user(
            username='creator1',
            email='creator1@example.com',
            password='testpassword123',
            first_name='Creative',
            last_name='Person'
        )
        self.creator.profile.bio = 'I make outfits'
        self.creator.profile.portfolio_url = 'https://example.com'
        self.creator.profile.is_hireable = True
        self.creator.profile.save()

        self.user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpassword123',
            first_name='Regular',
            last_name='User'
        )

    def test_creator_profile_public(self):
        response = self.client.get(f'/api/profile/creators/{self.creator.username}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'creator1')
        self.assertEqual(response.data['display_name'], 'Creative Person')
        self.assertEqual(response.data['bio'], 'I make outfits')
        self.assertEqual(response.data['portfolio_url'], 'https://example.com')
        self.assertTrue(response.data['is_hireable'])
        self.assertEqual(response.data['follower_count'], 0)
        self.assertEqual(response.data['outfit_count'], 0)
        self.assertEqual(response.data['total_likes'], 0)
        self.assertFalse(response.data['is_following'])
        self.assertEqual(response.data['outfits'], [])

    def test_follow_creator(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/profile/creators/{self.creator.username}/follow/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['following'])
        self.assertTrue(
            CreatorFollow.objects.filter(follower=self.user, following=self.creator).exists()
        )

    def test_follow_idempotent(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/profile/creators/{self.creator.username}/follow/')
        response = self.client.post(f'/api/profile/creators/{self.creator.username}/follow/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['following'])
        self.assertEqual(
            CreatorFollow.objects.filter(follower=self.user, following=self.creator).count(), 1
        )

    def test_unfollow_creator(self):
        CreatorFollow.objects.create(follower=self.user, following=self.creator)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/profile/creators/{self.creator.username}/follow/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['following'])
        self.assertFalse(
            CreatorFollow.objects.filter(follower=self.user, following=self.creator).exists()
        )

    def test_cannot_follow_self(self):
        self.client.force_authenticate(user=self.creator)
        response = self.client.post(f'/api/profile/creators/{self.creator.username}/follow/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_follow_unauthenticated(self):
        response = self.client.post(f'/api/profile/creators/{self.creator.username}/follow/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_enquiry_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/profile/creators/{self.creator.username}/enquiry/',
            {'message': 'I would like to hire you for a project.'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Enquiry sent successfully.')

    def test_enquiry_not_hireable(self):
        self.creator.profile.is_hireable = False
        self.creator.profile.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/profile/creators/{self.creator.username}/enquiry/',
            {'message': 'I would like to hire you.'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
