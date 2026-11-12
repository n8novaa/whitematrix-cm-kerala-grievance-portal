from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from apps.accounts.models import User
from .models import AIRecommendation, ActionTakenReport, Attachment, DepartmentAssignment, Grievance, GrievanceHistory
from apps.departments.models import Department
import tempfile


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class CitizenGrievanceAPITests(APITestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(email='one@example.test', password='Test-pass-994!')
        self.other = User.objects.create_user(email='two@example.test', password='Test-pass-994!')
        self.client.force_authenticate(self.citizen)

    def payload(self):
        return {'district': 'Ernakulam', 'category': 'Roads', 'subject': 'Pothole near school', 'description': 'Large pothole creates danger for children.'}

    def test_submission_generates_reference_and_initial_history(self):
        response = self.client.post('/api/v1/grievances/', self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        grievance = Grievance.objects.get()
        self.assertRegex(grievance.reference_number, r'^CMK-\d{4}-[A-F0-9]{32}$')
        self.assertEqual(grievance.citizen, self.citizen)
        self.assertEqual(grievance.history.count(), 1)
        self.assertEqual(response.data['reference_number'], grievance.reference_number)

    def test_submission_rejects_districts_outside_kerala(self):
        response = self.client.post('/api/v1/grievances/', {**self.payload(), 'district': 'Bengaluru'}, format='json')
        self.assertEqual(response.status_code, 400)

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
        self.assertEqual(response.data['history'][0]['responsible_user_role'], User.Role.CITIZEN)
        self.assertNotIn('Private', str(response.data))
        self.assertNotIn('description', response.data)

    def test_cmo_can_move_submitted_grievance_to_under_review(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        cmo = User.objects.create_user(email='review-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        response = self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.assertEqual(response.status_code, 200, response.data)
        grievance.refresh_from_db()
        entry = grievance.history.get()
        self.assertEqual(grievance.status, Grievance.Status.UNDER_REVIEW)
        self.assertEqual(entry.responsible_user, cmo)
        self.assertTrue(entry.is_internal)

    def test_officer_and_citizen_cannot_start_cmo_review_or_publish_unassigned_updates(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        officer = User.objects.create_user(email='review-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER)
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Unauthorized public update', 'is_public': True}).status_code, 404)
        self.client.force_authenticate(self.citizen)
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Citizen writes public update', 'is_public': True}).status_code, 403)

    def test_officer_can_publish_citizen_visible_progress_without_leaking_private_notes(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='PUB', description='Roads')
        officer = User.objects.create_user(email='public-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='public-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        DepartmentAssignment.objects.create(grievance=grievance, department=department, officer=officer, assigned_by=cmo)
        self.client.force_authenticate(officer)
        response = self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Inspection visit scheduled for tomorrow.', 'is_public': True})
        self.assertEqual(response.status_code, 201, response.data)
        tracked = self.client.get(f'/api/v1/grievances/track/{grievance.reference_number}/')
        self.assertIn('Inspection visit scheduled for tomorrow.', str(tracked.data))
        self.assertIn('OFFICER', str(tracked.data))

    def test_cmo_accepts_ai_suggestion_as_audited_official_values(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='AIP', description='Roads')
        recommendation = AIRecommendation.objects.create(grievance=grievance, department=department, category='Road Safety', priority='HIGH', summary='Inspect roadway hazard.')
        cmo = User.objects.create_user(email='ai-decision-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        response = self.client.get('/api/v1/grievances/cmo/queue/')
        self.assertEqual(response.data[0]['ai_recommendation']['decision'], 'PENDING')
        adopted = self.client.post(f'/api/v1/grievances/{grievance.pk}/ai-recommendation/decision/', {'decision': 'ACCEPTED'})
        self.assertEqual(adopted.status_code, 200, adopted.data)
        grievance.refresh_from_db()
        recommendation.refresh_from_db()
        self.assertEqual((grievance.department, grievance.category, grievance.priority), (department, 'Road Safety', 'HIGH'))
        self.assertEqual(recommendation.reviewed_by, cmo)
        self.assertIsNotNone(recommendation.reviewed_at)
        self.assertTrue(grievance.history.get().is_internal)
        self.client.force_authenticate(self.citizen)
        self.assertIsNone(self.client.get(f'/api/v1/grievances/{grievance.pk}/').data['ai_recommendation'])

    def test_cmo_can_override_ai_suggestion_and_officer_cannot(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        original = Department.objects.create(name='Public Works', code='AIO', description='Roads')
        replacement = Department.objects.create(name='Water', code='WTR', description='Water services')
        AIRecommendation.objects.create(grievance=grievance, department=original, category='Roads', priority='HIGH', summary='Fix the road.')
        officer = User.objects.create_user(email='ai-override-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER)
        self.client.force_authenticate(officer)
        url = f'/api/v1/grievances/{grievance.pk}/ai-recommendation/decision/'
        body = {'decision': 'OVERRIDDEN', 'department_id': replacement.pk, 'category': 'Infrastructure', 'priority': 'LOW'}
        self.assertEqual(self.client.post(url, body).status_code, 403)
        cmo = User.objects.create_user(email='ai-override-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        response = self.client.post(url, body)
        self.assertEqual(response.status_code, 200, response.data)
        grievance.refresh_from_db()
        self.assertEqual((grievance.department, grievance.category, grievance.priority), (replacement, 'Infrastructure', 'LOW'))

    def test_cmo_public_progress_is_visible_and_cmo_escalation_is_audited(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        cmo = User.objects.create_user(email='escalation-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        officer = User.objects.create_user(email='escalation-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER)
        self.client.force_authenticate(cmo)
        update = self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'The case has been escalated for urgent district review.', 'is_public': True})
        self.assertEqual(update.status_code, 201, update.data)
        escalation = self.client.post(f'/api/v1/grievances/{grievance.pk}/escalations/', {'reason': 'Urgent public safety concern requires executive oversight.'})
        self.assertEqual(escalation.status_code, 201, escalation.data)
        self.assertEqual(escalation.data['raised_by'], cmo.email)
        self.assertEqual(self.client.get(f'/api/v1/grievances/{grievance.pk}/escalations/').data[0]['id'], escalation.data['id'])
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/escalations/', {'reason': 'Unauthorized escalation attempt reason.'}).status_code, 403)
        public = self.client.get(f'/api/v1/grievances/track/{grievance.reference_number}/')
        self.assertIn('district review', str(public.data))
        self.assertNotIn('executive oversight', str(public.data))

    def test_cmo_queue_filters_district_category_priority_and_status(self):
        grievance = Grievance.objects.create(citizen=self.citizen, district='Ernakulam', category='Roads', priority='HIGH', **{key:value for key,value in self.payload().items() if key not in ('district','category')})
        cmo = User.objects.create_user(email='filters-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        for query in ('district=Ernakulam', 'category=Roads', 'priority=HIGH', 'status=SUBMITTED'):
            response = self.client.get(f'/api/v1/grievances/cmo/queue/?{query}')
            self.assertEqual([row['id'] for row in response.data], [grievance.pk], query)
        self.assertEqual(self.client.get('/api/v1/grievances/cmo/queue/?district=Kollam').data, [])

    def test_cmo_queue_rejects_invalid_filter_values(self):
        cmo = User.objects.create_user(email='invalid-filters-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        for query in ('status=UNKNOWN', 'priority=URGENT', 'district=Bengaluru', 'department=not-an-id'):
            with self.subTest(query=query):
                response = self.client.get(f'/api/v1/grievances/cmo/queue/?{query}')
                self.assertEqual(response.status_code, 400, response.data)

    def test_assignment_must_follow_under_review_and_records_required_sequence(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='FLOW', description='Roads')
        officer = User.objects.create_user(email='flow-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='flow-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        path = f'/api/v1/grievances/{grievance.pk}/assign/'
        payload = {'department_id': department.pk, 'officer_id': officer.pk}
        skipped = self.client.post(path, payload)
        self.assertEqual(skipped.status_code, 400)
        grievance.refresh_from_db()
        self.assertEqual(grievance.status, Grievance.Status.SUBMITTED)
        self.assertFalse(grievance.assignments.exists())
        reviewed = self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.assertEqual(reviewed.status_code, 200)
        assigned = self.client.post(path, payload)
        self.assertEqual(assigned.status_code, 200, assigned.data)
        grievance.refresh_from_db()
        self.assertEqual(grievance.status, Grievance.Status.IN_PROGRESS)
        self.assertEqual(list(grievance.history.values_list('previous_status', 'new_status')), [('SUBMITTED', 'UNDER_REVIEW'), ('UNDER_REVIEW', 'IN_PROGRESS')])

    def test_only_one_action_report_can_be_pending(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.IN_PROGRESS, **self.payload())
        department = Department.objects.create(name='Public Works', code='PEND', description='Roads')
        officer = User.objects.create_user(email='pending-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='pending-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        DepartmentAssignment.objects.create(grievance=grievance, department=department, officer=officer, assigned_by=cmo)
        self.client.force_authenticate(officer)
        endpoint = f'/api/v1/grievances/{grievance.pk}/action-reports/'
        first = self.client.post(endpoint, {'report': 'Initial inspection report is complete.'})
        second = self.client.post(endpoint, {'report': 'A second report should be blocked.'})
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 409, second.data)
        self.assertEqual(grievance.action_reports.filter(review_status=ActionTakenReport.ReviewStatus.PENDING).count(), 1)

    def test_resolution_requires_latest_report_accepted_and_nonempty_remarks(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.IN_PROGRESS, **self.payload())
        cmo = User.objects.create_user(email='latest-report-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        older = ActionTakenReport.objects.create(grievance=grievance, officer=self.other, report='An earlier action report was accepted.', review_status=ActionTakenReport.ReviewStatus.ACCEPTED)
        latest = ActionTakenReport.objects.create(grievance=grievance, officer=self.other, report='The latest action report is pending review.')
        self.client.force_authenticate(cmo)
        endpoint = f'/api/v1/grievances/{grievance.pk}/resolve/'
        blocked = self.client.post(endpoint, {'remarks': 'Resolution note is sufficiently clear.'})
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('latest', blocked.data['detail'].lower())
        latest.review_status = ActionTakenReport.ReviewStatus.ACCEPTED
        latest.save(update_fields=('review_status',))
        missing_remarks = self.client.post(endpoint, {'remarks': '   '})
        whitespace_remarks = self.client.post(endpoint, {'remarks': '          '})
        self.assertEqual(missing_remarks.status_code, 400)
        self.assertEqual(whitespace_remarks.status_code, 400)
        resolved = self.client.post(endpoint, {'remarks': 'The latest accepted report confirms completion.'})
        self.assertEqual(resolved.status_code, 200, resolved.data)

    def test_report_review_requires_valid_remarks_for_return_and_limits_length(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.IN_PROGRESS, **self.payload())
        report = ActionTakenReport.objects.create(grievance=grievance, officer=self.other, report='Completed investigation report.')
        cmo = User.objects.create_user(email='review-remarks-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        endpoint = f'/api/v1/grievances/action-reports/{report.pk}/review/'
        missing = self.client.post(endpoint, {'decision': 'RETURNED', 'remarks': '  '})
        too_long = self.client.post(endpoint, {'decision': 'ACCEPTED', 'remarks': 'x' * 5001})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(too_long.status_code, 400)
        report.refresh_from_db()
        self.assertEqual(report.review_status, ActionTakenReport.ReviewStatus.PENDING)

    def test_assignment_remarks_are_visible_to_officers_but_never_to_citizens(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='PWD3', description='Roads')
        officer = User.objects.create_user(email='notes-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='notes-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': officer.pk, 'remarks': 'Internal repair coordination note.'})
        self.client.force_authenticate(self.citizen)
        citizen_detail = self.client.get(f'/api/v1/grievances/{grievance.pk}/')
        public_track = self.client.get(f'/api/v1/grievances/track/{grievance.reference_number}/')
        self.assertNotIn('Internal repair coordination note.', str(citizen_detail.data))
        self.assertNotIn('Internal repair coordination note.', str(public_track.data))
        self.client.force_authenticate(officer)
        officer_case = self.client.get('/api/v1/grievances/officer/queue/').data[0]
        self.assertEqual(officer_case['assignment']['remarks'], 'Internal repair coordination note.')

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
        file = SimpleUploadedFile('photo.jpg', b'\xff\xd8\xffjpeg-bytes', content_type='image/jpeg')
        response = self.client.post('/api/v1/grievances/', {**self.payload(), 'attachments': file}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        attachment = Attachment.objects.get()
        self.client.force_authenticate(self.other)
        denied = self.client.get(f'/api/v1/grievances/{attachment.grievance_id}/attachments/{attachment.pk}/')
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.citizen)
        allowed = self.client.get(f'/api/v1/grievances/{attachment.grievance_id}/attachments/{attachment.pk}/')
        self.assertEqual(allowed.status_code, 200)

    def test_cmo_and_active_assigned_officer_can_download_attachments(self):
        file = SimpleUploadedFile('photo.jpg', b'\xff\xd8\xffjpeg-bytes', content_type='image/jpeg')
        created = self.client.post('/api/v1/grievances/', {**self.payload(), 'attachments': file}, format='multipart')
        self.assertEqual(created.status_code, 201, created.data)
        attachment = Attachment.objects.get()
        grievance = attachment.grievance
        department = Department.objects.create(name='Health', code='ATCH', description='Health')
        officer = User.objects.create_user(email='attachment-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='attachment-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        reviewed = self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        assigned = self.client.post(
            f'/api/v1/grievances/{grievance.pk}/assign/',
            {'department_id': department.pk, 'officer_id': officer.pk},
        )
        self.assertEqual(assigned.status_code, 200, assigned.data)
        endpoint = f'/api/v1/grievances/{grievance.pk}/attachments/{attachment.pk}/'
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.get(endpoint).status_code, 200)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(endpoint).status_code, 403)
        self.client.force_authenticate(cmo)
        self.assertEqual(self.client.get(endpoint).status_code, 200)

    def test_attachment_rejects_fake_image_with_allowed_extension(self):
        response = self.client.post('/api/v1/grievances/', {**self.payload(), 'attachments': SimpleUploadedFile('photo.jpg', b'not-an-image', content_type='image/jpeg')}, format='multipart')
        self.assertEqual(response.status_code, 400)

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
        reviewing = self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.assertEqual(reviewing.status_code, 200, reviewing.data)
        assigned = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': officer.pk})
        self.assertEqual(assigned.status_code, 200, assigned.data)
        self.client.force_authenticate(officer)
        self.assertEqual(len(self.client.get('/api/v1/grievances/officer/queue/').data), 1)
        forbidden_resolution = self.client.post(f'/api/v1/grievances/{grievance.pk}/resolve/', {'remarks': 'Officer cannot resolve.'})
        self.assertEqual(forbidden_resolution.status_code, 403)
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
        self.client.force_authenticate(self.citizen)
        feedback = self.client.post(f'/api/v1/grievances/{grievance.pk}/feedback/', {'rating': 4, 'comments': 'The repair is holding.'})
        self.assertEqual(feedback.status_code, 201, feedback.data)
        reopened = self.client.post(f'/api/v1/grievances/{grievance.pk}/reopen/', {'remarks': 'The repair failed again after rain.'})
        self.assertEqual(reopened.status_code, 200, reopened.data)
        self.assertEqual(reopened.data['status'], Grievance.Status.REOPENED)
        self.assertEqual(reopened.data['feedback']['rating'], 4)

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
        department = Department.objects.create(name='Road Maintenance', code='RDM', description='Road repairs')
        officer = User.objects.create_user(email='reopen-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='reopen-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Reopened case review started.'})
        assigned = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': officer.pk})
        self.assertEqual(assigned.status_code, 200, assigned.data)
        self.assertEqual(assigned.data['status'], Grievance.Status.IN_PROGRESS)

    def test_resolved_citizen_can_leave_feedback_and_read_it_back(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.RESOLVED, **self.payload())
        response = self.client.post(f'/api/v1/grievances/{grievance.pk}/feedback/', {'rating': 4, 'comments': 'The repair was completed.'})
        self.assertEqual(response.status_code, 201, response.data)
        detail = self.client.get(f'/api/v1/grievances/{grievance.pk}/')
        self.assertEqual(detail.data['feedback']['rating'], 4)
        self.assertEqual(detail.data['feedback']['comments'], 'The repair was completed.')

    def test_feedback_can_be_submitted_again_after_reopened_cycle_is_resolved(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.RESOLVED, **self.payload())
        GrievanceHistory.objects.create(grievance=grievance, previous_status='IN_PROGRESS', new_status='RESOLVED', responsible_user=self.other)
        first_feedback = self.client.post(f'/api/v1/grievances/{grievance.pk}/feedback/', {'rating': 3, 'comments': 'First repair was temporary.'})
        self.assertEqual(first_feedback.status_code, 201, first_feedback.data)
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/feedback/', {'rating': 4}).status_code, 409)

        reopened = self.client.post(f'/api/v1/grievances/{grievance.pk}/reopen/', {'remarks': 'The repair failed again.'})
        self.assertEqual(reopened.status_code, 200, reopened.data)
        department = Department.objects.create(name='Road Maintenance', code='FDBK', description='Road repairs')
        officer = User.objects.create_user(email='feedback-cycle-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='feedback-cycle-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Reviewing the returned repair.'})
        assignment = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': officer.pk})
        self.assertEqual(assignment.status_code, 200, assignment.data)
        self.client.force_authenticate(officer)
        report = self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'The road was repaired again and checked.'})
        self.assertEqual(report.status_code, 201, report.data)
        self.client.force_authenticate(cmo)
        accepted = self.client.post(f"/api/v1/grievances/action-reports/{report.data['id']}/review/", {'decision': 'ACCEPTED'})
        self.assertEqual(accepted.status_code, 200, accepted.data)
        resolved = self.client.post(f'/api/v1/grievances/{grievance.pk}/resolve/', {'remarks': 'The latest repair has been verified.'})
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.client.force_authenticate(self.citizen)
        second_feedback = self.client.post(f'/api/v1/grievances/{grievance.pk}/feedback/', {'rating': 5, 'comments': 'The second repair is holding.'})
        self.assertEqual(second_feedback.status_code, 201, second_feedback.data)
        detail = self.client.get(f'/api/v1/grievances/{grievance.pk}/')
        self.assertEqual(detail.data['current_resolution_cycle'], 2)
        self.assertEqual(detail.data['feedback']['resolution_cycle'], 2)
        self.assertEqual(grievance.feedbacks.count(), 2)

    def test_health_endpoint_checks_ready_services_without_exposing_details(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'status': 'ok'})

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
        self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': first.pk})
        self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': second.pk})
        self.client.force_authenticate(first)
        self.assertEqual(self.client.get('/api/v1/grievances/officer/queue/').data, [])
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Old assignment access attempt'}).status_code, 404)

    def test_cmo_assignment_is_visible_only_to_current_officer_and_reassignment_preserves_history(self):
        grievance = Grievance.objects.create(citizen=self.citizen, **self.payload())
        department = Department.objects.create(name='Public Works', code='QUEUE', description='Roads')
        other_department = Department.objects.create(name='Health', code='QUEUE-HEALTH', description='Health')
        first = User.objects.create_user(email='queue-first@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        second = User.objects.create_user(email='queue-second@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        same_department_peer = User.objects.create_user(email='queue-peer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        different_department = User.objects.create_user(email='queue-other-dept@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=other_department)
        cmo = User.objects.create_user(email='queue-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)

        reviewed = self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Initial review started.'})
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        assigned = self.client.post(
            f'/api/v1/grievances/{grievance.pk}/assign/',
            {'department_id': department.pk, 'officer_id': first.pk},
        )
        self.assertEqual(assigned.status_code, 200, assigned.data)
        first_assignment = DepartmentAssignment.objects.get(grievance=grievance, is_active=True)
        self.assertEqual((first_assignment.department_id, first_assignment.officer_id), (department.pk, first.pk))
        self.assertEqual([item['id'] for item in self.client.get('/api/v1/grievances/cmo/queue/').data], [grievance.pk])

        self.client.force_authenticate(first)
        first_queue = self.client.get('/api/v1/grievances/officer/queue/')
        self.assertEqual([item['id'] for item in first_queue.data], [grievance.pk])
        self.assertEqual(first_queue.data[0]['assignment']['officer_id'], first.pk)
        self.assertEqual(self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Assigned officer can access this case.'}).status_code, 201)

        for unauthorized_officer in (same_department_peer, different_department):
            with self.subTest(officer=unauthorized_officer.email):
                self.client.force_authenticate(unauthorized_officer)
                self.assertEqual(self.client.get('/api/v1/grievances/officer/queue/').data, [])
                self.assertEqual(
                    self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Unauthorized access attempt.'}).status_code,
                    404,
                )

        self.client.force_authenticate(cmo)
        reassigned = self.client.post(
            f'/api/v1/grievances/{grievance.pk}/assign/',
            {'department_id': department.pk, 'officer_id': second.pk},
        )
        self.assertEqual(reassigned.status_code, 200, reassigned.data)
        assignments = list(DepartmentAssignment.objects.filter(grievance=grievance).order_by('assigned_at', 'pk'))
        self.assertEqual(len(assignments), 2)
        self.assertEqual([assignment.is_active for assignment in assignments], [False, True])

        self.client.force_authenticate(first)
        self.assertEqual(self.client.get('/api/v1/grievances/officer/queue/').data, [])
        self.client.force_authenticate(second)
        second_queue = self.client.get('/api/v1/grievances/officer/queue/')
        self.assertEqual([item['id'] for item in second_queue.data], [grievance.pk])
        self.assertEqual(second_queue.data[0]['assignment']['officer_id'], second.pk)

    def test_resolved_grievance_rejects_reassignment_and_officer_updates(self):
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.RESOLVED, **self.payload())
        department = Department.objects.create(name='Public Works', code='PWD4', description='Roads')
        officer = User.objects.create_user(email='resolved-officer@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='resolved-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        self.client.force_authenticate(cmo)
        rejected = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': officer.pk})
        self.assertEqual(rejected.status_code, 400)
        DepartmentAssignment.objects.create(grievance=grievance, department=department, officer=officer, assigned_by=cmo)
        self.client.force_authenticate(officer)
        update = self.client.post(f'/api/v1/grievances/{grievance.pk}/updates/', {'remarks': 'Late update attempt after resolution.'})
        report = self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'Late action report attempt.'})
        self.assertEqual(update.status_code, 400)
        self.assertEqual(report.status_code, 400)

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

    def test_reopened_resolution_requires_current_cycle_report_from_active_officer(self):
        department = Department.objects.create(name='Public Works', code='CYCLE', description='Roads')
        first_officer = User.objects.create_user(email='cycle-first@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        current_officer = User.objects.create_user(email='cycle-current@example.test', password='Test-pass-994!', role=User.Role.OFFICER, department=department)
        cmo = User.objects.create_user(email='cycle-cmo@example.test', password='Test-pass-994!', role=User.Role.CMO)
        grievance = Grievance.objects.create(citizen=self.citizen, status=Grievance.Status.RESOLVED, department=department, **self.payload())
        DepartmentAssignment.objects.create(grievance=grievance, department=department, officer=first_officer, assigned_by=cmo)
        ActionTakenReport.objects.create(grievance=grievance, officer=first_officer, report='Accepted before the first resolution.', review_status=ActionTakenReport.ReviewStatus.ACCEPTED)

        self.client.force_authenticate(self.citizen)
        reopened = self.client.post(f'/api/v1/grievances/{grievance.pk}/reopen/', {'remarks': 'The repair failed again after rain.'})
        self.assertEqual(reopened.status_code, 200, reopened.data)
        self.client.force_authenticate(cmo)
        self.client.post(f'/api/v1/grievances/{grievance.pk}/cmo/review/', {'remarks': 'Reviewing the reopened grievance.'})
        assigned = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': first_officer.pk})
        self.assertEqual(assigned.status_code, 200, assigned.data)

        resolve_url = f'/api/v1/grievances/{grievance.pk}/resolve/'
        stale_report_resolution = self.client.post(resolve_url, {'remarks': 'The earlier report is insufficient.'})
        self.assertEqual(stale_report_resolution.status_code, 400, stale_report_resolution.data)

        self.client.force_authenticate(first_officer)
        first_cycle_report = self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'The first reopened cycle repair was completed.'})
        self.assertEqual(first_cycle_report.status_code, 201, first_cycle_report.data)
        self.client.force_authenticate(cmo)
        reviewed = self.client.post(f"/api/v1/grievances/action-reports/{first_cycle_report.data['id']}/review/", {'decision': 'ACCEPTED'})
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        reassigned = self.client.post(f'/api/v1/grievances/{grievance.pk}/assign/', {'department_id': department.pk, 'officer_id': current_officer.pk})
        self.assertEqual(reassigned.status_code, 200, reassigned.data)
        stale_assignee_resolution = self.client.post(resolve_url, {'remarks': 'The previous assignee report is insufficient.'})
        self.assertEqual(stale_assignee_resolution.status_code, 400, stale_assignee_resolution.data)

        self.client.force_authenticate(current_officer)
        current_report = self.client.post(f'/api/v1/grievances/{grievance.pk}/action-reports/', {'report': 'The currently assigned officer completed the renewed repair.'})
        self.assertEqual(current_report.status_code, 201, current_report.data)
        self.client.force_authenticate(cmo)
        reviewed = self.client.post(f"/api/v1/grievances/action-reports/{current_report.data['id']}/review/", {'decision': 'ACCEPTED'})
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        resolved = self.client.post(resolve_url, {'remarks': 'The latest cycle report confirms completion.'})
        self.assertEqual(resolved.status_code, 200, resolved.data)
