from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from user.models import User

class GoogleAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/google/'

    @override_settings(ENABLE_GOOGLE_AUTH=False)
    def test_google_auth_disabled_returns_404(self):
        """Test that the endpoint returns 404 when the feature flag is disabled."""
        response = self.client.post(self.url, {'id_token': 'some-token'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(ENABLE_GOOGLE_AUTH=True)
    @override_settings(ENABLE_GOOGLE_AUTH=True)
    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_auth_success(self, mock_verify):
        """Test successful Google login creates user and returns tokens."""
        # Mock Google response
        mock_verify.return_value = {
            'email': 'test@example.com',
            'sub': '123456789',
            'name': 'Test User'
        }

        response = self.client.post(self.url, {'id_token': 'valid-token'})
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify user created
        user = User.objects.get(email='test@example.com')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'test@example.com')

    @override_settings(ENABLE_GOOGLE_AUTH=True)
    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_auth_invalid_token(self, mock_verify):
        """Test invalid token returns 401."""
        # Mock verification failure
        mock_verify.side_effect = ValueError("Invalid token")

        response = self.client.post(self.url, {'id_token': 'invalid-token'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
