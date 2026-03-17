from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from user.models import User
from store.models import Store


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
        self.assertIn('user', response.data)
        self.assertIn('uuid', response.data['user'])
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertIn('role', response.data['user'])
        self.assertIn('account_type', response.data['user'])

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
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')
        self.assertIn('uuid', response.data['user'])
        self.assertIn('role', response.data['user'])
        self.assertIn('account_type', response.data['user'])

        # Verify user was created in database
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.username, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')

    def test_register_password_mismatch(self):
        """Test registration fails when passwords don't match."""
        data = {
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
            'email': 'newuser@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_duplicate_email(self):
        """Test registration fails with duplicate email."""
        User.objects.create_user(username='existing@example.com',
                                 email='existing@example.com', password='password123')

        data = {
            'email': 'existing@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_missing_required_fields(self):
        """Test registration fails when required fields are missing."""
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)


class LoginTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.url = '/api/auth/login/'
        self.user = self.create_test_user()

    def test_login_success(self):
        """Test successful login returns user data and tokens."""
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertIn('uuid', response.data['user'])
        self.assertIn('role', response.data['user'])
        self.assertIn('account_type', response.data['user'])

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


class StoreRegistrationTests(AuthTestCase):
    """Tests for store registration endpoint."""

    def setUp(self):
        super().setUp()
        self.url = '/api/auth/store/register/'

    def test_store_register_success(self):
        """Test successful store registration creates user and store."""
        data = {
            'email': 'store@example.com',
            'password': 'securepassword123',
            'store_name': 'My Awesome Store'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'store@example.com')
        self.assertIn('uuid', response.data['user'])
        self.assertEqual(response.data['user']['role'], 'User')
        self.assertEqual(response.data['user']['account_type'], 'Store')

        # Verify user was created with correct account_type
        user = User.objects.get(email='store@example.com')
        self.assertEqual(user.account_type, User.AccountType.STORE)

        # Verify store was created
        store = Store.objects.get(owner=user)
        self.assertEqual(store.name, 'My Awesome Store')
        self.assertEqual(store.slug, 'my-awesome-store')

    def test_store_register_duplicate_email(self):
        """Test store registration fails with duplicate email."""
        User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='password123'
        )

        data = {
            'email': 'existing@example.com',
            'password': 'securepassword123',
            'store_name': 'My Store'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_store_register_duplicate_store_name(self):
        """Test store registration fails with duplicate store name (slug)."""
        # Create existing store
        existing_user = User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='password123'
        )
        Store.objects.create(
            owner=existing_user,
            name='My Store',
            slug='my-store'
        )

        data = {
            'email': 'newstore@example.com',
            'password': 'securepassword123',
            'store_name': 'My Store'  # Same name, will generate same slug
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('store_name', response.data)

    def test_store_register_password_too_short(self):
        """Test store registration fails when password is too short."""
        data = {
            'email': 'store@example.com',
            'password': 'short',
            'store_name': 'My Store'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_store_register_missing_required_fields(self):
        """Test store registration fails when required fields are missing."""
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
        self.assertIn('store_name', response.data)

    def test_store_register_invalid_email(self):
        """Test store registration fails with invalid email format."""
        data = {
            'email': 'not-an-email',
            'password': 'securepassword123',
            'store_name': 'My Store'
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class ChangePasswordTests(AuthTestCase):
    """Tests for the change password endpoint."""

    def setUp(self):
        super().setUp()
        self.url = '/api/auth/change-password/'
        self.user = self.create_test_user()
        self.client.force_authenticate(user=self.user)

    def test_change_password_success(self):
        """Test successful password change."""
        data = {
            'current_password': 'testpassword123',
            'new_password': 'newsecurepassword456',
            'new_password_confirm': 'newsecurepassword456',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Password updated successfully.')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newsecurepassword456'))

    def test_change_password_wrong_current(self):
        """Test change password fails with wrong current password."""
        data = {
            'current_password': 'wrongpassword',
            'new_password': 'newsecurepassword456',
            'new_password_confirm': 'newsecurepassword456',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)

    def test_change_password_mismatch(self):
        """Test change password fails when new passwords do not match."""
        data = {
            'current_password': 'testpassword123',
            'new_password': 'newsecurepassword456',
            'new_password_confirm': 'differentpassword789',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password_confirm', response.data)

    def test_change_password_too_short(self):
        """Test change password fails when new password is too short."""
        data = {
            'current_password': 'testpassword123',
            'new_password': 'short',
            'new_password_confirm': 'short',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    def test_change_password_missing_fields(self):
        """Test change password fails when fields are missing."""
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)
        self.assertIn('new_password', response.data)
        self.assertIn('new_password_confirm', response.data)

    def test_change_password_unauthenticated(self):
        """Test change password fails without authentication."""
        self.client.force_authenticate(user=None)

        data = {
            'current_password': 'testpassword123',
            'new_password': 'newsecurepassword456',
            'new_password_confirm': 'newsecurepassword456',
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
