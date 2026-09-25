from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_cannot_choose_privileged_role(self):
        response = self.client.post('/api/account/register/', {
            'username': 'new-user',
            'password': 'safe-password-123',
            'role': 'SUPER_ADMIN',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(User.objects.get(username='new-user').role, 'EMPLOYEE')

    def test_user_cannot_change_own_role_or_active_state(self):
        user = User.objects.create_user(
            username='employee', password='password-123', role='EMPLOYEE'
        )
        self.client.force_authenticate(user)
        response = self.client.patch('/api/account/me/', {
            'role': 'SUPER_ADMIN',
            'is_active': False,
            'first_name': 'Updated',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        user.refresh_from_db()
        self.assertEqual(user.role, 'EMPLOYEE')
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, 'Updated')

    def test_jwt_login_and_refresh(self):
        User.objects.create_user(username='jwt-user', password='password-123')
        response = self.client.post('/api/account/login/', {
            'username': 'jwt-user', 'password': 'password-123'
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        response = self.client.post('/api/account/token/refresh/', {
            'refresh': response.data['refresh']
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data)
