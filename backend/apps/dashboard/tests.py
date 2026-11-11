from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.grievances.models import Grievance


class CMOStatisticsTests(APITestCase):
    def test_statistics_include_database_district_breakdown_and_restrict_roles(self):
        citizen = User.objects.create_user(email='stats-citizen@example.test', password='Test-pass-994!')
        User.objects.create_user(email='stats-citizen2@example.test', password='Test-pass-994!')
        Grievance.objects.create(citizen=citizen, district='Ernakulam', category='Roads', subject='Road 1', description='A sufficiently long road report.')
        Grievance.objects.create(citizen=citizen, district='Kollam', category='Water', subject='Water 1', description='A sufficiently long water report.')
        cmo = User.objects.create_user(email='stats-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        response = self.client.get('/api/v1/dashboard/cmo/statistics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['by_district'], [{'district': 'Ernakulam', 'count': 1}, {'district': 'Kollam', 'count': 1}])
        self.client.force_authenticate(citizen)
        self.assertEqual(self.client.get('/api/v1/dashboard/cmo/statistics/').status_code, 403)
