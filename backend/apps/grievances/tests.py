from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from apps.accounts.models import User
from .models import ActionTakenReport, Attachment, Grievance, GrievanceHistory
from apps.departments.models import Department
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

    def test_cmo_assigns_and_officer_submits_report_then_cmo_resolves(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='PWD', description='Roads')
        officer = User.objects.create_user(email='officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        assigned = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': officer.pk})
        self.assertEqual(assigned.status_code, 200, assigned.data)
        self.client.force_authenticate(officer)
        self.assertEqual(len(self.client.get('/api/v1/grievances/officer/queue/').data), 1)
        update = self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Road crew inspected the damaged section.'})
        self.assertEqual(update.status_code, 201, update.data)
        report = self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'Road repaired and inspected.'})
        self.assertEqual(report.status_code, 201, report.data)
        self.client.force_authenticate(cmo)
        reviewed = self.client.post(f"/api/v1/grievances/action-reports/{report.data['id']}/review/", {'decision': 'ACCEPTED', 'remarks': 'Verified'})
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        resolved = self.client.post(f'/api/v1/grievances/{grievance.pk}/resolve/', {'remarks': 'Resolution confirmed.'})
        self.assertEqual(resolved.status_code, 200, resolved.data)
        grievance.refresh_from_db()
        self.assertEqual(grievance.status, Grievance.Status.RESOLVED)
        history = list(grievance.history.order_by('created_at').values_list('previous_status', 'new_status'))
        self.assertEqual(history[-1], (Grievance.Status.IN_PROGRESS, Grievance.Status.RESOLVED))
        self.assertNotIn('Road crew inspected', str(self.client.get(f'/api/v1/grievances/{grievance.pk}/').data))

    def test_cmo_cannot_resolve_before_report_acceptance(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        cmo = User.objects.create_user(email='cmo2@example.test', password='Test-pass-994!', role=User.Role.CMO)
        from .models import ActionTakenReport
        ActionTakenReport.objects.create(grievance=grievance, officer=self.other, report='Investigation report completed.')
        self.client.force_authenticate(cmo)
        response = self.client.post(f'/api/v1/grievances/{grievance.pk}/resolve/', {})
        self.assertEqual(response.status_code, 400)
        grievance.refresh_from_db()
        self.assertEqual(grievance.status, Grievance.Status.SUBMITTED)

    def test_non_citizen_cannot_use_citizen_grievance_endpoints(self):
        officer = User.objects.create_user(email='role@example.test', password='Test-pass-994!', role=User.Role.OFFICER)
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.get('/api/v1/grievances/').status_code, 403)
        self.assertEqual(self.client.post('/api/v1/grievances/', self.payload()).status_code, 403)

    def test_cmo_can_return_report_and_officer_can_submit_replacement(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.IN_PROGRESS, **self.payload())
        department = Department.objects.create(name='Public Works', code='PWD', description='Roads')
        officer = User.objects.create_user(email='assigned@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='reviewer@example.test', password='Test-pass-994!', role=User.Role.CMO)
        grievance.department = department
        grievance.save(update_fields=('department',))
        from .models import DepartmentAssignment
        DepartmentAssignment.objects.create(grievance=grievance, department=department, officer=officer, assigned_by=cmo)
        first = ActionTakenReport.objects.create(grievance=grievance, officer=officer, report='Initial inspection is complete.')

        self.client.force_authenticate(cmo)
        returned = self.client.post(f'/api/v1/grievances/action-reports/{first.pk}/review/', {'decision': 'RETURNED', 'remarks': 'Please include the repair date.'})
        self.assertEqual(returned.status_code, 200)
        first.refresh_from_db()
        self.assertEqual(first.review_status, ActionTakenReport.ReviewStatus.RETURNED)
        self.assertEqual(first.review_remarks, 'Please include the repair date.')

        self.client.force_authenticate(officer)
        replacement = self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'The road repair was completed on 10 November.'})
        self.assertEqual(replacement.status_code, 201, replacement.data)

    def test_citizen_reopen_changes_status_and_keeps_internal_remarks_private(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.RESOLVED, **self.payload())
        GrievanceHistory.objects.create(grievance=grievance, previous_status='IN_PROGRESS', new_status='RESOLVED', responsible_user=self.other, remarks='internal-only review note', is_internal=True)
        response = self.client.post(f'/api/v1/grievances/{grievance.pk}/reopen/', {'remarks': 'The repair did not last.'})
        self.assertEqual(response.status_code, 200, response.data)
        grievance.refresh_from_db()
        self.assertEqual(grievance.status, Grievance.Status.REOPENED)
        tracked = self.client.get(f'/api/v1/grievances/track/{grievance.reference_number}/')
        own = self.client.get(f'/api/v1/grievances/{grievance.pk}/')
        self.assertNotIn('internal-only review note', str(tracked.data))
        self.assertNotIn('internal-only review note', str(own.data))
        self.assertIn('The repair did not last.', str(tracked.data))

    def test_officer_cannot_read_or_update_unassigned_grievance(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Health', code='HLT', description='Health')
        officer = User.objects.create_user(email='unassigned@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.get('/api/v1/grievances/officer/queue/').data, [])
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'An unauthorized report attempt.'}).status_code, 404)
        self.assertIn(self.client.get(f'/api/v1/grievances/{grievance.pk}/attachments/999/').status_code, (403, 404))

    def test_reassigned_officer_loses_queue_and_object_access(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='PWD2', description='Roads')
        first = User.objects.create_user(email='first-assignee@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        second = User.objects.create_user(email='second-assignee@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='reassign-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': first.pk})
        self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': second.pk})
        self.client.force_authenticate(first)
        self.assertEqual(self.client.get('/api/v1/grievances/officer/queue/').data, [])
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Old assignment access attempt'}).status_code, 404)

    def test_cmo_resolution_is_atomic_and_requires_accepted_report(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        cmo = User.objects.create_user(email='atomic-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        ActionTakenReport.objects.create(grievance=grievance, officer=self.other, report='Returned report text.', review_status=ActionTakenReport.ReviewStatus.RETURNED)
        self.client.force_authenticate(cmo)
        response = self.client.post(f'/api/v1/grievances/{grievance.pk}/resolve/', {'remarks': 'Should not be applied.'})
        self.assertEqual(response.status_code, 400)
        grievance.refresh_from_db()
        self.assertEqual(grievance.status, Grievance.Status.SUBMITTED)
        self.assertEqual(grievance.history.count(), 0)
