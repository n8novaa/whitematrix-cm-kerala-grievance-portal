from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache
from .models import User


class AuthenticationAPITests(APITestCase):
    password = 'Valid-Password-934!'

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email='citizen@example.test', password=self.password)

    def test_public_registration_creates_citizen_only(self):
        response = self.client.post('/api/v1/auth/register/', {
            'email': 'New.Citizen@example.test', 'password': self.password, 'confirm_password': self.password,
            'first_name': 'New', 'last_name': 'Citizen', 'mobile_number': '+919876543210', 'role': 'CMO',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='new.citizen@example.test')
        self.assertEqual(user.role, User.Role.CITIZEN)
        self.assertEqual(user.mobile_number, '+919876543210')
        self.assertNotIn('password', response.data)

    def test_registration_requires_full_name_mobile_and_matching_password_confirmation(self):
        base = {'email': 'complete@example.test', 'first_name': 'Complete', 'last_name': 'Citizen', 'mobile_number': '9876543210', 'password': self.password, 'confirm_password': self.password}
        self.assertEqual(self.client.post('/api/v1/auth/register/', base, format='json').status_code, 201)
        for update in (
            {'last_name': ''}, {'mobile_number': ''}, {'mobile_number': 'not-a-mobile'},
            {'confirm_password': 'Different-Password-99!'},
        ):
            with self.subTest(update=update):
                body = {**base, 'email': f"invalid-{len(User.objects.all())}-{len(update)}@example.test", **update}
                response = self.client.post('/api/v1/auth/register/', body, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post('/api/v1/auth/login/', {'email': self.user.email, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post('/api/v1/auth/login/', {'email': self.user.email, 'password': 'wrong'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_is_throttled(self):
        cache.clear()
        payload = {'email': self.user.email, 'password': 'wrong'}
        for _ in range(10):
            self.assertEqual(self.client.post('/api/v1/auth/login/', payload, format='json').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login/', payload, format='json').status_code, 429)
        cache.clear()

    def test_refresh_returns_new_access_token(self):
        login = self.client.post('/api/v1/auth/login/', {'email': self.user.email, 'password': self.password}, format='json')
        response = self.client.post('/api/v1/auth/refresh/', {'refresh': login.data['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post('/api/v1/auth/login/', {'email': self.user.email, 'password': self.password}, format='json')
        refresh = login.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        logout = self.client.post('/api/v1/auth/logout/', {'refresh': refresh}, format='json')
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.post('/api/v1/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_auth_and_cannot_change_role_or_email(self):
        self.assertEqual(self.client.get('/api/v1/auth/profile/').status_code, status.HTTP_401_UNAUTHORIZED)
        login = self.client.post('/api/v1/auth/login/', {'email': self.user.email, 'password': self.password}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.patch('/api/v1/auth/profile/', {
            'first_name': 'Updated', 'email': 'attacker@example.test', 'role': 'CMO',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.email, 'citizen@example.test')
        self.assertEqual(self.user.role, User.Role.CITIZEN)
