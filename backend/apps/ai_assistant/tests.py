from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.departments.models import Department


class GrievanceAnalysisAPITests(APITestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(email='ai-citizen@example.test', password='Test-pass-994!')
        self.officer = User.objects.create_user(email='ai-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER)
        self.payload = {'description': 'A damaged road creates a serious safety risk near the local school.'}

    def test_analysis_requires_authenticated_citizen(self):
        self.assertEqual(self.client.post('/api/v1/ai/analyze/', self.payload).status_code, 401)
        self.client.force_authenticate(self.officer)
        self.assertEqual(self.client.post('/api/v1/ai/analyze/', self.payload).status_code, 403)

    @override_settings(GEMINI_API_KEY='')
    def test_missing_provider_key_returns_clear_unavailable_response(self):
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 503)
        self.assertIn('unavailable', response.data['detail'].lower())

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('apps.ai_assistant.views.genai.Client')
    def test_valid_ai_output_is_returned_as_advisory_only(self, client_factory):
        department = Department.objects.create(name='Public Works', code='PWD', description='Roads')
        client_factory.return_value.models.generate_content.return_value.text = '{"department_code":"PWD","category":"Roads","priority":"HIGH","summary":"A road hazard requires inspection."}'
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['advisory'])
        self.assertEqual(response.data['department_code'], department.code)
        self.assertEqual(response.data['priority'], 'HIGH')

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('apps.ai_assistant.views.genai.Client')
    def test_provider_exception_returns_gateway_error_without_leaking_details(self, client_factory):
        client_factory.return_value.models.generate_content.side_effect = RuntimeError('private provider diagnostic')
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('private provider diagnostic', str(response.data))

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('apps.ai_assistant.views.genai.Client')
    def test_invalid_provider_json_values_return_gateway_error(self, client_factory):
        department = Department.objects.create(name='Public Works', code='PWD', description='Roads')
        mock_client = client_factory.return_value
        mock_client.models.generate_content.return_value.text = '{"department_code":"UNKNOWN","category":"Road","priority":"URGENT","summary":"Safety risk"}'
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 502)
        self.assertNotIn(department.code, response.data.get('detail', ''))
