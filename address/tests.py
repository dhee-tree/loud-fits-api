from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from .models import Address


class AddressTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='addr@example.com', password='testpass123')

    def test_list_empty(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/addresses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_first_address_is_default(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'label': 'Home',
            'address_line_1': '123 Main St',
            'city': 'London',
            'postcode': 'SW1A 1AA',
            'country': 'United Kingdom',
        }
        response = self.client.post('/api/addresses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_default'])

    def test_second_address_not_default(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/addresses/', {
            'address_line_1': '123 Main St', 'city': 'London',
            'postcode': 'SW1A 1AA', 'country': 'UK',
        })
        response = self.client.post('/api/addresses/', {
            'label': 'Work',
            'address_line_1': '456 Office Rd', 'city': 'Manchester',
            'postcode': 'M1 1AA', 'country': 'UK',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_default'])

    def test_set_default(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/addresses/', {
            'address_line_1': '123 Main St', 'city': 'London',
            'postcode': 'SW1A 1AA', 'country': 'UK',
        })
        res2 = self.client.post('/api/addresses/', {
            'address_line_1': '456 Office Rd', 'city': 'Manchester',
            'postcode': 'M1 1AA', 'country': 'UK',
        })
        second_uuid = res2.data['uuid']

        response = self.client.post(f'/api/addresses/{second_uuid}/set-default/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_default'])

        first = Address.objects.filter(user=self.user).exclude(uuid=second_uuid).first()
        self.assertFalse(first.is_default)

    def test_delete_default_reassigns(self):
        self.client.force_authenticate(user=self.user)
        res1 = self.client.post('/api/addresses/', {
            'address_line_1': '123 Main St', 'city': 'London',
            'postcode': 'SW1A 1AA', 'country': 'UK',
        })
        self.client.post('/api/addresses/', {
            'address_line_1': '456 Office Rd', 'city': 'Manchester',
            'postcode': 'M1 1AA', 'country': 'UK',
        })

        self.client.delete(f'/api/addresses/{res1.data["uuid"]}/')
        remaining = Address.objects.filter(user=self.user).first()
        self.assertTrue(remaining.is_default)

    def test_update_address(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/addresses/', {
            'address_line_1': '123 Main St', 'city': 'London',
            'postcode': 'SW1A 1AA', 'country': 'UK',
        })
        response = self.client.patch(
            f'/api/addresses/{res.data["uuid"]}/',
            {'city': 'Bristol'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['city'], 'Bristol')

    def test_unauthenticated(self):
        response = self.client.get('/api/addresses/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
