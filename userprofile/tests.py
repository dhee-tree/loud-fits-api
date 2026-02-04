from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from .models import Profile


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
        # Profile is created automatically via signal

    def test_get_profile_authenticated(self):
        """Test getting profile when authenticated."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('uuid', response.data)
        self.assertIn('shopping_preference', response.data)
        self.assertIn('avatar_size', response.data)
        self.assertIn('stylist_enabled', response.data)
        self.assertEqual(response.data['stylist_enabled'], False)

    def test_get_profile_unauthenticated(self):
        """Test getting profile when not authenticated."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile_update_shopping_preference(self):
        """Test updating profile shopping_preference."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'shopping_preference': 'MALE'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['shopping_preference'], 'MALE')

        # Verify database was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.shopping_preference, 'MALE')

    def test_patch_profile_enable_stylist(self):
        """Test enabling stylist mode."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'stylist_enabled': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stylist_enabled'], True)

    def test_patch_profile_invalid_shopping_preference(self):
        """Test updating profile with invalid shopping_preference."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'shopping_preference': 'INVALID'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
