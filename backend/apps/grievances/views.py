from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.throttling import ScopedRateThrottle
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.accounts.permissions import IsCMO, IsOfficer, IsCitizen
from apps.accounts.models import User
from apps.departments.models import Department
from .models import AIRecommendation, ActionTakenReport, Attachment, CitizenFeedback, ContactEnquiry, DepartmentAssignment, Grievance, GrievanceEscalation, GrievanceHistory
from .serializers import GrievanceSerializer


def transition(grievance, new_status, actor, remarks='', internal=False):
    allowed = {
        Grievance.Status.SUBMITTED: {Grievance.Status.UNDER_REVIEW, Grievance.Status.IN_PROGRESS},
        Grievance.Status.UNDER_REVIEW: {Grievance.Status.IN_PROGRESS},
        Grievance.Status.IN_PROGRESS: {Grievance.Status.RESOLVED},
        Grievance.Status.RESOLVED: {Grievance.Status.REOPENED},
        Grievance.Status.REOPENED: {Grievance.Status.UNDER_REVIEW, Grievance.Status.IN_PROGRESS},
    }
    if new_status not in allowed.get(grievance.status, set()):
        raise serializers.ValidationError({'status': f'Invalid transition from {grievance.status} to {new_status}.'})
    previous = grievance.status
    grievance.status = new_status
    grievance.save(update_fields=('status', 'updated_at'))
    GrievanceHistory.objects.create(grievance=grievance, previous_status=previous, new_status=new_status, responsible_user=actor, remarks=remarks, is_internal=internal)


class CitizenGrievanceListCreateView(generics.ListCreateAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = (permissions.IsAuthenticated, IsCitizen)

    def get_queryset(self):
        if self.request.user.role != 'CITIZEN':
            raise PermissionDenied('Citizen role required.')
        return Grievance.objects.filter(citizen=self.request.user).select_related('department').prefetch_related('history', 'attachments')


class CitizenGrievanceDetailView(generics.RetrieveAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = (permissions.IsAuthenticated, IsCitizen)

    def get_queryset(self):
        if self.request.user.role != 'CITIZEN':
            raise PermissionDenied('Citizen role required.')
        return Grievance.objects.filter(citizen=self.request.user).select_related('department').prefetch_related('history', 'attachments')


class TrackGrievanceView(generics.RetrieveAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'reference_number'
    lookup_url_kwarg = 'reference_number'
    queryset = Grievance.objects.select_related('department').prefetch_related('history', 'attachments')
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'tracking'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['tracking'] = True
        return context


class AttachmentDownloadView(APIView):
    def get(self, request, grievance_id, attachment_id):
        if not request.user.is_authenticated:
            raise PermissionDenied()
        grievance = get_object_or_404(Grievance, pk=grievance_id)
        if request.user.role == 'CITIZEN' and grievance.citizen_id != request.user.pk:
            raise PermissionDenied()
        if request.user.role == 'OFFICER' and not grievance.assignments.filter(officer=request.user, is_active=True).exists():
            raise PermissionDenied()
        if request.user.role not in ('CITIZEN', 'CMO', 'OFFICER'):
            raise PermissionDenied()
        attachment = get_object_or_404(Attachment, pk=attachment_id, grievance=grievance)
        return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.original_name)


class CMOGrievanceQueueView(generics.ListAPIView):
    permission_classes = (IsCMO,)
    serializer_class = GrievanceSerializer
    def get_queryset(self):
        queryset = Grievance.objects.select_related('citizen', 'department').prefetch_related('history', 'attachments', 'action_reports__officer')
        status_filter = self.request.query_params.get('status')
        department_filter = self.request.query_params.get('department')
        district_filter = self.request.query_params.get('district')
        category_filter = self.request.query_params.get('category')
        priority_filter = self.request.query_params.get('priority')
        search = self.request.query_params.get('search', '').strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if department_filter:
            queryset = queryset.filter(department_id=department_filter)
        if district_filter:
            queryset = queryset.filter(district__iexact=district_filter.strip())
        if category_filter:
            queryset = queryset.filter(category__iexact=category_filter.strip())
        if priority_filter in Grievance.Priority.values:
            queryset = queryset.filter(priority=priority_filter)
        if search:
            queryset = queryset.filter(Q(reference_number__icontains=search) | Q(subject__icontains=search) | Q(category__icontains=search))
        return queryset


class CMOReviewGrievanceView(APIView):
    permission_classes = (IsCMO,)

    def post(self, request, pk):
        remarks = serializers.CharField(required=False, allow_blank=True, max_length=5000).run_validation(request.data.get('remarks', ''))
        with transaction.atomic():
            grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=pk)
            transition(grievance, Grievance.Status.UNDER_REVIEW, request.user, remarks, internal=True)
        return Response(GrievanceSerializer(grievance, context={'request': request}).data)


class EscalateGrievanceView(APIView):
    permission_classes = (IsCMO,)

    def get(self, request, pk):
        get_object_or_404(Grievance, pk=pk)
        records = GrievanceEscalation.objects.filter(grievance_id=pk).select_related('raised_by').order_by('created_at')
        return Response([{'id': item.pk, 'reason': item.reason, 'created_at': item.created_at, 'raised_by': item.raised_by.email} for item in records])

    def post(self, request, pk):
        reason = serializers.CharField(min_length=10, max_length=5000).run_validation(request.data.get('reason', ''))
        with transaction.atomic():
            grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=pk)
            if grievance.status == Grievance.Status.RESOLVED:
                raise serializers.ValidationError({'status': 'Resolved grievances cannot be escalated.'})
            escalation = GrievanceEscalation.objects.create(grievance=grievance, reason=reason.strip(), raised_by=request.user)
        return Response({'id': escalation.pk, 'reason': escalation.reason, 'created_at': escalation.created_at, 'raised_by': request.user.email}, status=201)


class AIRecommendationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=('ACCEPTED', 'OVERRIDDEN'))
    department_id = serializers.IntegerField(required=False)
    category = serializers.CharField(required=False, max_length=80)
    priority = serializers.ChoiceField(choices=Grievance.Priority.choices, required=False)

    def validate(self, attrs):
        if attrs['decision'] == 'OVERRIDDEN' and not all(key in attrs for key in ('department_id', 'category', 'priority')):
            raise serializers.ValidationError('Override requires department_id, category, and priority.')
        if attrs.get('category') is not None:
            attrs['category'] = attrs['category'].strip()
            if not attrs['category']:
                raise serializers.ValidationError({'category': 'Category cannot be blank.'})
        return attrs


class AIRecommendationDecisionView(APIView):
    permission_classes = (IsCMO,)

    def post(self, request, pk):
        serializer = AIRecommendationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=pk)
            if grievance.status == Grievance.Status.RESOLVED:
                raise serializers.ValidationError({'status': 'Resolved grievances cannot update AI decisions.'})
            recommendation = get_object_or_404(AIRecommendation.objects.select_for_update().select_related('department'), grievance=grievance)
            if recommendation.decision != AIRecommendation.Decision.PENDING:
                raise serializers.ValidationError({'decision': 'This recommendation has already been reviewed.'})
            if data['decision'] == 'ACCEPTED':
                department = recommendation.department
                if department is None or not department.is_active:
                    raise serializers.ValidationError({'decision': 'The suggested department is no longer active; submit an override.'})
                category, priority = recommendation.category, recommendation.priority
            else:
                department = get_object_or_404(Department, pk=data['department_id'], is_active=True)
                category, priority = data['category'].strip(), data['priority']
            grievance.department = department
            grievance.category = category
            grievance.priority = priority
            grievance.save(update_fields=('department', 'category', 'priority', 'updated_at'))
            recommendation.decision = data['decision']
            recommendation.reviewed_by = request.user
            recommendation.reviewed_at = timezone.now()
            recommendation.save(update_fields=('decision', 'reviewed_by', 'reviewed_at'))
            GrievanceHistory.objects.create(grievance=grievance, previous_status=grievance.status, new_status=grievance.status, responsible_user=request.user, remarks=f"AI recommendation {data['decision'].lower()} and adopted as official values.", is_internal=True)
        return Response(GrievanceSerializer(grievance, context={'request': request}).data)


class AssignmentInputSerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    officer_id = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            attrs['department'] = Department.objects.get(pk=attrs['department_id'], is_active=True)
        except Department.DoesNotExist:
            raise serializers.ValidationError({'department_id': 'Select an active department.'})
        try:
            attrs['officer'] = User.objects.get(pk=attrs['officer_id'], role=User.Role.OFFICER, department=attrs['department'], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError({'officer_id': 'Select an officer in the chosen department.'})
        return attrs


class AssignGrievanceView(APIView):
    permission_classes = (IsCMO,)

    def post(self, request, pk):
        serializer = AssignmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=pk)
            if grievance.status == Grievance.Status.RESOLVED:
                raise serializers.ValidationError({'status': 'Resolved grievances cannot be reassigned.'})
            data = serializer.validated_data
            grievance.department = data['department']
            grievance.save(update_fields=('department', 'updated_at'))
            grievance.assignments.filter(is_active=True).update(is_active=False)
            DepartmentAssignment.objects.create(grievance=grievance, department=data['department'], officer=data['officer'], assigned_by=request.user, remarks=data.get('remarks', ''))
            if grievance.status in (Grievance.Status.SUBMITTED, Grievance.Status.UNDER_REVIEW, Grievance.Status.REOPENED):
                transition(grievance, Grievance.Status.IN_PROGRESS, request.user, data.get('remarks', ''), internal=True)
        return Response(GrievanceSerializer(grievance, context={'request': request}).data)


class OfficerQueueView(generics.ListAPIView):
    permission_classes = (IsOfficer,)
    serializer_class = GrievanceSerializer

    def get_queryset(self):
        return Grievance.objects.filter(assignments__officer=self.request.user, assignments__is_active=True).select_related('department').prefetch_related('history', 'attachments', 'action_reports__officer').distinct()


class ActionReportInputSerializer(serializers.Serializer):
    report = serializers.CharField(min_length=10)


class SubmitActionReportView(APIView):
    permission_classes = (IsOfficer,)

    def post(self, request, pk):
        serializer = ActionReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            grievance = get_object_or_404(
                Grievance.objects.select_for_update(),
                pk=pk,
                assignments__officer=request.user,
                assignments__is_active=True,
            )
            if grievance.status == Grievance.Status.RESOLVED:
                raise serializers.ValidationError({'status': 'Resolved grievances cannot receive new reports.'})
            report = ActionTakenReport.objects.create(grievance=grievance, officer=request.user, report=serializer.validated_data['report'])
        return Response({'id': report.pk, 'review_status': report.review_status, 'created_at': report.created_at}, status=201)


class OfficerProgressUpdateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        remarks = serializers.CharField(min_length=5, max_length=5000).run_validation(request.data.get('remarks', ''))
        is_public = serializers.BooleanField(required=False, default=False).run_validation(request.data.get('is_public', False))
        if request.user.role not in (User.Role.CMO, User.Role.OFFICER):
            raise PermissionDenied('Only CMO administrators and officers can post progress updates.')
        with transaction.atomic():
            grievance_qs = Grievance.objects.select_for_update()
            if request.user.role == User.Role.OFFICER:
                grievance_qs = grievance_qs.filter(assignments__officer=request.user, assignments__is_active=True)
            grievance = get_object_or_404(grievance_qs, pk=pk)
            if grievance.status == Grievance.Status.RESOLVED:
                raise serializers.ValidationError({'status': 'Resolved grievances cannot receive progress updates.'})
            history = GrievanceHistory.objects.create(
                grievance=grievance,
                previous_status=grievance.status,
                new_status=grievance.status,
                responsible_user=request.user,
                remarks=remarks,
                is_internal=not is_public,
            )
        return Response({'id': history.pk, 'created_at': history.created_at}, status=201)


class CMOResolveView(APIView):
    permission_classes = (IsCMO,)

    def post(self, request, pk):
        remarks = serializers.CharField(required=False, allow_blank=True, max_length=5000).run_validation(request.data.get('remarks', ''))
        with transaction.atomic():
            grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=pk)
            accepted_report_exists = ActionTakenReport.objects.filter(
                grievance=grievance,
                review_status=ActionTakenReport.ReviewStatus.ACCEPTED,
            ).exists()
            if not accepted_report_exists:
                return Response({'detail': 'An accepted action report is required.'}, status=400)
            transition(grievance, Grievance.Status.RESOLVED, request.user, remarks, internal=False)
        return Response(GrievanceSerializer(grievance, context={'request': request}).data)


class CMOReportReviewView(APIView):
    permission_classes = (IsCMO,)

    def post(self, request, report_id):
        decision = request.data.get('decision')
        if decision not in ('ACCEPTED', 'RETURNED'):
            return Response({'detail': 'Decision must be ACCEPTED or RETURNED.'}, status=400)
        with transaction.atomic():
            report = get_object_or_404(ActionTakenReport.objects.select_for_update(), pk=report_id)
            if report.review_status != ActionTakenReport.ReviewStatus.PENDING:
                return Response({'detail': 'Only pending reports can be reviewed.'}, status=409)
            report.review_status = decision
            report.review_remarks = request.data.get('remarks', '')
            report.save(update_fields=('review_status', 'review_remarks'))
        return Response({'id': report.pk, 'review_status': report.review_status})


class CitizenReopenView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsCitizen)

    def post(self, request, pk):
        grievance = get_object_or_404(Grievance, pk=pk, citizen=request.user, status=Grievance.Status.RESOLVED)
        remarks = request.data.get('remarks', '').strip()
        if not remarks:
            raise serializers.ValidationError({'remarks': 'Explain why the grievance needs to be reopened.'})
        with transaction.atomic():
            grievance = get_object_or_404(
                Grievance.objects.select_for_update(),
                pk=pk,
                citizen=request.user,
                status=Grievance.Status.RESOLVED,
            )
            transition(grievance, Grievance.Status.REOPENED, request.user, remarks)
        return Response(GrievanceSerializer(grievance, context={'request': request}).data)


class FeedbackInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comments = serializers.CharField(required=False, allow_blank=True)


class CitizenFeedbackView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsCitizen)

    def post(self, request, pk):
        grievance = get_object_or_404(Grievance, pk=pk, citizen=request.user, status=Grievance.Status.RESOLVED)
        serializer = FeedbackInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback, created = CitizenFeedback.objects.get_or_create(grievance=grievance, defaults={'citizen': request.user, **serializer.validated_data})
        if not created:
            return Response({'detail': 'Feedback has already been submitted.'}, status=409)
        return Response({'rating': feedback.rating, 'comments': feedback.comments}, status=201)


class ContactEnquiryInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactEnquiry
        fields = ('name', 'email', 'subject', 'message')


class ContactEnquiryView(generics.CreateAPIView):
    serializer_class = ContactEnquiryInputSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'public_form'
