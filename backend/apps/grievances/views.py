from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from django.db import transaction
from django.db.models import Q
from apps.accounts.permissions import IsCMO, IsOfficer, IsCitizen
from apps.accounts.models import User
from apps.departments.models import Department
from .models import ActionTakenReport, Attachment, CitizenFeedback, ContactEnquiry, DepartmentAssignment, Grievance, GrievanceHistory
from .serializers import GrievanceSerializer


def transition(grievance, new_status, actor, remarks='', internal=False):
    allowed = {
        Grievance.Status.SUBMITTED: {Grievance.Status.UNDER_REVIEW, Grievance.Status.IN_PROGRESS},
        Grievance.Status.UNDER_REVIEW: {Grievance.Status.IN_PROGRESS},
        Grievance.Status.IN_PROGRESS: {Grievance.Status.RESOLVED},
        Grievance.Status.RESOLVED: {Grievance.Status.REOPENED},
        Grievance.Status.REOPENED: {Grievance.Status.IN_PROGRESS},
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
        search = self.request.query_params.get('search', '').strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if department_filter:
            queryset = queryset.filter(department_id=department_filter)
        if search:
            queryset = queryset.filter(Q(reference_number__icontains=search) | Q(subject__icontains=search) | Q(category__icontains=search))
        return queryset


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
            attrs['officer'] = User.objects.get(pk=attrs['officer_id'], role=User.Role.OFFICER, department=attrs['department'])
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
            data = serializer.validated_data
            grievance.department = data['department']
            grievance.save(update_fields=('department', 'updated_at'))
            grievance.assignments.filter(is_active=True).update(is_active=False)
            DepartmentAssignment.objects.create(grievance=grievance, department=data['department'], officer=data['officer'], assigned_by=request.user, remarks=data.get('remarks', ''))
            if grievance.status in (Grievance.Status.SUBMITTED, Grievance.Status.UNDER_REVIEW):
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
        grievance = get_object_or_404(Grievance, pk=pk, assignments__officer=request.user, assignments__is_active=True)
        serializer = ActionReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = ActionTakenReport.objects.create(grievance=grievance, officer=request.user, report=serializer.validated_data['report'])
        return Response({'id': report.pk, 'review_status': report.review_status, 'created_at': report.created_at}, status=201)


class OfficerProgressUpdateView(APIView):
    permission_classes = (IsOfficer,)

    def post(self, request, pk):
        remarks = serializers.CharField(min_length=5, max_length=5000).run_validation(request.data.get('remarks', ''))
        with transaction.atomic():
            grievance = get_object_or_404(
                Grievance.objects.select_for_update(),
                pk=pk,
                assignments__officer=request.user,
                assignments__is_active=True,
            )
            history = GrievanceHistory.objects.create(
                grievance=grievance,
                previous_status=grievance.status,
                new_status=grievance.status,
                responsible_user=request.user,
                remarks=remarks,
                is_internal=True,
            )
        return Response({'id': history.pk, 'created_at': history.created_at}, status=201)


class CMOResolveView(APIView):
    permission_classes = (IsCMO,)

    def post(self, request, pk):
        with transaction.atomic():
            grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=pk)
            accepted_report_exists = ActionTakenReport.objects.filter(
                grievance=grievance,
                review_status=ActionTakenReport.ReviewStatus.ACCEPTED,
            ).exists()
            if not accepted_report_exists:
                return Response({'detail': 'An accepted action report is required.'}, status=400)
            transition(grievance, Grievance.Status.RESOLVED, request.user, request.data.get('remarks', ''), internal=False)
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
