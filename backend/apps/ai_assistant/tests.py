from unittest.mock import patch
from types import SimpleNamespace
import time

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts.models import User
from apps.departments.models import Department
from apps.grievances.models import AIRecommendation, Grievance


class GrievanceAnalysisAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.citizen = User.objects.create_user(email='ai-citizen@example.test', password='Test-pass-994!')
        self.officer = User.objects.create_user(email='ai-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER)
        self.payload = {'description': 'A damaged road creates a serious safety risk near the local school.'}

    def test_analysis_requires_authenticated_citizen(self):
        self.assertEqual(self.client.post('/api/v1/ai/analyze/', self.payload).status_code, 401)
        self.client.force_authenticate(self.officer)
        self.assertEqual(self.client.post('/api/v1/ai/analyze/', self.payload).status_code, 403)

    @override_settings(GEMINI_API_KEY='')
    def test_future_cache_entry_does_not_produce_excessive_retry_after(self):
        cache.clear()
        request = APIRequestFactory().post('/api/v1/ai/analyze/', self.payload)
        request.user = self.citizen
        throttle = ScopedRateThrottle()
        throttle.scope = 'ai_analysis'
        key = throttle.get_cache_key(request, SimpleNamespace(throttle_scope='ai_analysis'))
        limit = int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_analysis'].split('/')[0])
        _, duration = throttle.parse_rate(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_analysis'])
        cache.set(key, [time.time() + 3600] * limit, timeout=duration)
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('Retry-After', response)

    @override_settings(GEMINI_API_KEY='')
    def test_stale_cache_entries_do_not_block_ai_analysis(self):
        request = APIRequestFactory().post('/api/v1/ai/analyze/', self.payload)
        request.user = self.citizen
        throttle = ScopedRateThrottle()
        throttle.scope = 'ai_analysis'
        key = throttle.get_cache_key(request, SimpleNamespace(throttle_scope='ai_analysis'))
        limit = int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_analysis'].split('/')[0])
        _, duration = throttle.parse_rate(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_analysis'])
        cache.set(key, [time.time() - (duration * 2)] * limit, timeout=duration)
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('Retry-After', response)

    def test_ai_throttle_retry_after_stays_within_configured_window(self):
        cache.clear()
        request = APIRequestFactory().post('/api/v1/ai/analyze/', self.payload)
        request.user = self.citizen
        throttle = ScopedRateThrottle()
        throttle.scope = 'ai_analysis'
        key = throttle.get_cache_key(request, SimpleNamespace(throttle_scope='ai_analysis'))
        limit = int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_analysis'].split('/')[0])
        _, duration = throttle.parse_rate(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_analysis'])
        cache.set(key, [time.time()] * limit, timeout=duration)
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', self.payload)
        self.assertEqual(response.status_code, 429)
        self.assertGreaterEqual(int(response['Retry-After']), 0)
        self.assertLessEqual(int(response['Retry-After']), duration)

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
        client_factory.assert_called_once_with(api_key='test-key', http_options={'timeout': 30000})
        submitted = self.client.post('/api/v1/grievances/', {
            'district': 'Ernakulam', 'category': 'Roads', 'subject': 'School road hazard',
            'description': self.payload['description'], 'ai_recommendation_token': response.data['recommendation_token'],
        }, format='json')
        self.assertEqual(submitted.status_code, 201, submitted.data)
        self.assertEqual(AIRecommendation.objects.get(grievance_id=submitted.data['id']).priority, 'HIGH')

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('apps.ai_assistant.views.genai.Client')
    def test_ai_token_cannot_be_reused_for_different_grievance_text(self, client_factory):
        Department.objects.create(name='Public Works', code='PWD', description='Roads')
        client_factory.return_value.models.generate_content.return_value.text = '{"department_code":"PWD","category":"Roads","priority":"HIGH","summary":"Inspect the road."}'
        self.client.force_authenticate(self.citizen)
        analysis = self.client.post('/api/v1/ai/analyze/', self.payload)
        submitted = self.client.post('/api/v1/grievances/', {
            'district': 'Ernakulam', 'category': 'Roads', 'subject': 'Other issue',
            'description': 'A different and unrelated grievance description submitted by the citizen.',
            'ai_recommendation_token': analysis.data['recommendation_token'],
        }, format='json')
        self.assertEqual(submitted.status_code, 400)

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('apps.ai_assistant.views.genai.Client')
    def test_analysis_is_persisted_only_for_matching_owned_grievance(self, client_factory):
        department = Department.objects.create(name='Public Works', code='PWD', description='Roads')
        grievance = Grievance.objects.create(citizen=self.citizen, district='Ernakulam', category='Roads', subject='School road hazard', description=self.payload['description'])
        client_factory.return_value.models.generate_content.return_value.text = '{"department_code":"PWD","category":"Road Safety","priority":"HIGH","summary":"Inspect the school road hazard."}'
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', {**self.payload, 'grievance_id': grievance.pk})
        self.assertEqual(response.status_code, 200, response.data)
        recommendation = AIRecommendation.objects.get(grievance=grievance)
        self.assertEqual(recommendation.department, department)
        self.assertEqual(recommendation.priority, 'HIGH')

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('apps.ai_assistant.views.genai.Client')
    def test_analysis_cannot_attach_recommendation_to_another_citizens_case(self, client_factory):
        foreign = User.objects.create_user(email='foreign-ai@example.test', password='Test-pass-994!')
        grievance = Grievance.objects.create(citizen=foreign, district='Ernakulam', category='Roads', subject='Other citizen', description=self.payload['description'])
        self.client.force_authenticate(self.citizen)
        response = self.client.post('/api/v1/ai/analyze/', {**self.payload, 'grievance_id': grievance.pk})
        self.assertEqual(response.status_code, 404)

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
