from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APITestCase
from apps.accounts.models import User
from .models import Department


class DepartmentModelTests(TestCase):
    def test_department_creation_and_unique_code(self):
        department = Department.objects.create(name='Health', code='HEALTH', description='Health services')
        self.assertEqual(str(department), 'Health (HEALTH)')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Department.objects.create(name='Other Health', code='HEALTH', description='Duplicate code')


class DepartmentAPITests(APITestCase):
    def setUp(self):
        self.active = Department.objects.create(name='Health', code='HEALTH', description='Health services')
        self.inactive = Department.objects.create(name='Closed Office', code='CLOSED', description='Inactive', is_active=False)

    def test_listing_is_public_and_only_returns_active_departments(self):
        response = self.client.get('/api/v1/departments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['code'] for row in response.data], ['HEALTH'])
        self.assertNotIn('is_active', response.data[0])

    def test_detail_is_public_for_active_department(self):
        response = self.client.get(f'/api/v1/departments/{self.active.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 'HEALTH')

    def test_inactive_department_is_hidden_from_detail(self):
        response = self.client.get(f'/api/v1/departments/{self.inactive.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_api_is_read_only(self):
        response = self.client.post('/api/v1/departments/', {'name': 'Injected'})
        self.assertEqual(response.status_code, 405)


class DepartmentSeedCommandTests(TestCase):
    def test_seed_command_is_idempotent_and_preserves_existing_values(self):
        Department.objects.create(name='Custom Health Name', code='HEALTH', description='Custom description')
        call_command('seed_departments')
        count = Department.objects.count()
        call_command('seed_departments')
        self.assertEqual(Department.objects.count(), count)
        self.assertEqual(Department.objects.get(code='HEALTH').name, 'Custom Health Name')


class DemoOfficerSeedCommandTests(TestCase):
    def setUp(self):
        call_command('seed_departments')
        self.pwd = Department.objects.get(code='PWD')
        User.objects.create_user(
            email='officerpwd@gmail.com', password='PwdExisting-Secret!',
            role=User.Role.OFFICER, department=self.pwd,
        )

    def test_seed_creates_one_officer_per_non_pwd_department_and_preserves_pwd(self):
        with patch.dict('os.environ', {'DEMO_OFFICER_PASSWORD': 'Django@123'}):
            call_command('seed_demo_officers')

        expected = {
            'HEALTH': 'officerhealth@gmail.com',
            'LSGD': 'officerlsgd@gmail.com',
            'WATER': 'officerwater@gmail.com',
            'EDUCATION': 'officereducation@gmail.com',
            'KSEB': 'officerkseb@gmail.com',
        }
        for code, email in expected.items():
            officer = User.objects.get(email=email)
            self.assertEqual(officer.role, User.Role.OFFICER)
            self.assertEqual(officer.department.code, code)
            self.assertTrue(officer.check_password('Django@123'))
            self.assertEqual(User.objects.filter(department=officer.department, role=User.Role.OFFICER).count(), 1)

        self.assertEqual(User.objects.filter(department=self.pwd, role=User.Role.OFFICER).count(), 1)
        self.assertTrue(User.objects.get(email='officerpwd@gmail.com').check_password('PwdExisting-Secret!'))

    def test_seed_is_idempotent_and_does_not_reset_existing_passwords(self):
        with patch.dict('os.environ', {'DEMO_OFFICER_PASSWORD': 'Django@123'}):
            call_command('seed_demo_officers')
            officer = User.objects.get(email='officerhealth@gmail.com')
            officer.set_password('changed-by-operator')
            officer.save(update_fields=('password',))
            call_command('seed_demo_officers')

        self.assertTrue(officer.check_password('changed-by-operator'))
        self.assertEqual(User.objects.filter(role=User.Role.OFFICER).count(), 6)

    def test_seed_requires_configured_password(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(CommandError):
                call_command('seed_demo_officers')
