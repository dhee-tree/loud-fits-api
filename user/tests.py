from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User


class UserMeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/me/'
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User'
        )

    def test_get_me_authenticated(self):
        """Test getting current user details when authenticated."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'testuser@example.com')
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertEqual(response.data['full_name'], 'Test User')
        self.assertIn('uuid', response.data)
        self.assertIn('role', response.data)
        self.assertIn('account_type', response.data)
        self.assertIn('profile', response.data)
        self.assertIn('shopping_preference', response.data['profile'])
        self.assertIn('stylist_enabled', response.data['profile'])

    def test_get_me_unauthenticated(self):
        """Test getting current user details when not authenticated."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_me_update_name(self):
        """Test updating current user's name."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'first_name': 'Updated'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')

        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')

    def test_patch_me_cannot_change_email(self):
        """Test that email cannot be changed via patch."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url, {'email': 'newemail@example.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Email should remain unchanged (read_only)
        self.assertEqual(response.data['email'], 'testuser@example.com')
