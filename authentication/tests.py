from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from user.models import User


class AuthTestCase(TestCase):
    """Base test class with common setup for authentication tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test user once for all tests in the class."""
        cls.test_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
    
    def setUp(self):
        self.client = APIClient()
    
    def create_test_user(self, **kwargs):
        """Create a test user with default or custom data."""
        data = {**self.test_user_data, **kwargs}
        return User.objects.create_user(**data)


class GoogleAuthTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.url = '/api/auth/google/'

    @override_settings(ENABLE_GOOGLE_AUTH=False)
    def test_google_auth_disabled_returns_404(self):
        """Test that the endpoint returns 404 when the feature flag is disabled."""
        response = self.client.post(self.url, {'id_token': 'some-token'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(ENABLE_GOOGLE_AUTH=True)
    @patch('authentication.views.id_token.verify_oauth2_token')
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
    @patch('authentication.views.id_token.verify_oauth2_token')
    def test_google_auth_invalid_token(self, mock_verify):
        """Test invalid token returns 401."""
        # Mock verification failure
        mock_verify.side_effect = ValueError("Invalid token")

        response = self.client.post(self.url, {'id_token': 'invalid-token'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RegistrationTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.url = '/api/auth/register/'

    def test_register_success(self):
        """Test successful user registration."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'newuser')
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')

        # Verify user was created in database
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')

    def test_register_password_mismatch(self):
        """Test registration fails when passwords don't match."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepassword123',
            'password_confirm': 'differentpassword',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_register_password_too_short(self):
        """Test registration fails when password is too short."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_duplicate_username(self):
        """Test registration fails with duplicate username."""
        User.objects.create_user(username='existinguser', email='existing@example.com', password='password123')

        data = {
            'username': 'existinguser',
            'email': 'newuser@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_missing_required_fields(self):
        """Test registration fails when required fields are missing."""
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
        self.assertIn('password', response.data)


class LoginTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.url = '/api/auth/login/'
        self.user = self.create_test_user()

    def test_login_success(self):
        """Test successful login returns tokens."""
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        """Test login fails with wrong password."""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        """Test login fails with nonexistent user."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'somepassword'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_credentials(self):
        """Test login fails when credentials are missing."""
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenRefreshTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.url = '/api/auth/refresh/'
        self.user = self.create_test_user()
        # Login to get tokens
        login_response = self.client.post('/api/auth/login/', {
            'email': self.test_user_data['email'],
            'password': self.test_user_data['password']
        })
        self.refresh_token = login_response.data['refresh']

    def test_refresh_token_success(self):
        """Test successful token refresh."""
        response = self.client.post(self.url, {'refresh': self.refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_token_invalid(self):
        """Test refresh fails with invalid token."""
        response = self.client.post(self.url, {'refresh': 'invalid-token'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
