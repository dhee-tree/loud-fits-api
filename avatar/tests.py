from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from user.models import User
from .models import AvatarProfile


class AvatarApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='avatar@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )
        self.other_user = User.objects.create_user(
            email='other-avatar@example.com',
            password='testpass123',
            account_type=User.AccountType.USER,
        )

    def test_get_avatar_me_requires_authentication(self):
        response = self.client.get('/api/avatar/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_avatar_me_creates_default_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/avatar/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['config'],
            {
                'body_type': AvatarProfile.BODY_TYPE_MEDIUM,
                'skin_tone': AvatarProfile.SKIN_TONE_MEDIUM,
            },
        )
        self.assertTrue(AvatarProfile.objects.filter(user=self.user).exists())

    def test_get_avatar_me_returns_existing_profile(self):
        AvatarProfile.objects.create(
            user=self.user,
            config={
                'body_type': AvatarProfile.BODY_TYPE_LARGE,
                'skin_tone': AvatarProfile.SKIN_TONE_DEEP,
            },
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/avatar/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['config']['body_type'], AvatarProfile.BODY_TYPE_LARGE)
        self.assertEqual(response.data['config']['skin_tone'], AvatarProfile.SKIN_TONE_DEEP)

    def test_get_avatar_me_normalises_legacy_profile_values(self):
        AvatarProfile.objects.create(
            user=self.user,
            config={
                'body_type': 'slim',
                'skin_tone': 'fair',
            },
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/avatar/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['config']['body_type'], AvatarProfile.BODY_TYPE_SMALL)
        self.assertEqual(response.data['config']['skin_tone'], AvatarProfile.SKIN_TONE_LIGHT)

    def test_patch_avatar_me_updates_allowed_keys(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            '/api/avatar/me/',
            {
                'config': {
                    'body_type': AvatarProfile.BODY_TYPE_SMALL,
                    'skin_tone': AvatarProfile.SKIN_TONE_DEEP,
                }
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['config']['body_type'], AvatarProfile.BODY_TYPE_SMALL)
        self.assertEqual(response.data['config']['skin_tone'], AvatarProfile.SKIN_TONE_DEEP)

        profile = AvatarProfile.objects.get(user=self.user)
        self.assertEqual(profile.config['body_type'], AvatarProfile.BODY_TYPE_SMALL)
        self.assertEqual(profile.config['skin_tone'], AvatarProfile.SKIN_TONE_DEEP)

    def test_patch_avatar_me_rejects_unknown_key(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            '/api/avatar/me/',
            {'config': {'height': 'tall'}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('height', response.data['config'])

    def test_patch_avatar_me_rejects_invalid_values(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            '/api/avatar/me/',
            {'config': {'body_type': 'athletic'}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('body_type', response.data['config'])

    def test_patch_avatar_me_requires_config_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            '/api/avatar/me/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('config', response.data)

    def test_patch_avatar_me_only_updates_authenticated_user_profile(self):
        other_profile = AvatarProfile.objects.create(
            user=self.other_user,
            config=AvatarProfile.default_config(),
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            '/api/avatar/me/',
            {'config': {'skin_tone': AvatarProfile.SKIN_TONE_LIGHT}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_profile.refresh_from_db()
        self.assertEqual(
            other_profile.config,
            AvatarProfile.default_config(),
        )

    def test_get_avatar_templates_requires_authentication(self):
        response = self.client.get('/api/avatar/templates/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_avatar_templates_returns_registry_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/avatar/templates/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('version', response.data)
        self.assertIn('defaults', response.data)
        self.assertIn('top', response.data['defaults'])
        self.assertIn('bottom', response.data['defaults'])
        self.assertGreater(len(response.data['templates']), 0)
