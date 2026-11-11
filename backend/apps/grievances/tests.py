from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from apps.accounts.models import User
from .models import Attachment, Grievance, GrievanceHistory
import tempfile


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class CitizenGrievanceAPITests(APITestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(email='one@example.test', password='Test-pass-994!')
        self.other = User.objects.create_user(email='two@example.test', password='Test-pass-994!')
        self.client.force_authenticate(self.citizen)

    def payload(self):
        return {'category': 'Roads', 'subject': 'Pothole near school', 'description': 'Large pothole creates danger for children.'}

    def test_submission_generates_reference_and_initial_history(self):
        response = self.client.post('/api/v1/grievances/', self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        grievance = Grievance.objects.get()
        self.assertRegex(grievance.reference_number, r'^CMK-\d{4}-[A-F0-9]{8}$')
        self.assertEqual(grievance.citizen, self.citizen)
        self.assertEqual(grievance.history.count(), 1)
        self.assertEqual(response.data['reference_number'], grievance.reference_number)

    def test_list_and_detail_only_show_own_grievances(self):
        own = Grievance.objects.create(citizen=self.citizen, **self.payload())
        Grievance.objects.create(citizen=self.other, **self.payload())
        self.assertEqual(len(self.client.get('/api/v1/grievances/').data), 1)
        self.assertEqual(self.client.get(f'/api/v1/grievances/{own.pk}/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/grievances/{own.pk + 1}/').status_code, 404)

    def test_public_tracking_exposes_status_and_public_history_only(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        GrievanceHistory.objects.create(grievance=grievance, new_status='SUBMITTED', responsible_user=self.citizen, remarks='Received')
        GrievanceHistory.objects.create(grievance=grievance, new_status='UNDER_REVIEW', responsible_user=self.citizen, remarks='Private', is_internal=True)
        response = self.client.get(f'/api/v1/grievances/track/{grievance.reference_number}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['history']), 1)
        self.assertNotIn('Private', str(response.data))
        self.assertNotIn('description', response.data)

    def test_cannot_set_protected_fields(self):
        response = self.client.post('/api/v1/grievances/', {**self.payload(), 'priority': 'HIGH', 'status': 'RESOLVED', 'department': 1}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        grievance = Grievance.objects.get()
        self.assertEqual(grievance.priority, Grievance.Priority.MEDIUM)
        self.assertEqual(grievance.status, Grievance.Status.SUBMITTED)
        self.assertIsNone(grievance.department)

    def test_invalid_attachment_rejected(self):
        response = self.client.post('/api/v1/grievances/', {**self.payload(), 'attachments': SimpleUploadedFile('script.exe', b'bad', content_type='application/octet-stream')}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Grievance.objects.count(), 0)

    def test_valid_attachment_requires_owner_for_download(self):
        file = SimpleUploadedFile('photo.jpg', b'jpeg-bytes', content_type='image/jpeg')
        response = self.client.post('/api/v1/grievances/', {**self.payload(), 'attachments': file}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        attachment = Attachment.objects.get()
        self.client.force_authenticate(self.other)
        denied = self.client.get(f'/api/v1/grievances/{attachment.grievance_id}/attachments/{attachment.pk}/')
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.citizen)
        allowed = self.client.get(f'/api/v1/grievances/{attachment.grievance_id}/attachments/{attachment.pk}/')
        self.assertEqual(allowed.status_code, 200)

    def test_authentication_required_for_private_grievance_endpoints(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/grievances/').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/grievances/', self.payload()).status_code, 401)
