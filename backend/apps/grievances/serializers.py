from pathlib import Path
from django.db import transaction
from rest_framework import serializers
from .models import ActionTakenReport, Attachment, CitizenFeedback, DepartmentAssignment, Grievance, GrievanceHistory

MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}


class AttachmentInputSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Attachment
        fields = ('file',)

    def validate_file(self, value):
        if value.size > MAX_ATTACHMENT_SIZE:
            raise serializers.ValidationError('File must be 5 MB or smaller.')
        extension = Path(value.name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError('Only JPG, PNG, and PDF files are allowed.')
        expected_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.pdf': 'application/pdf'}
        if getattr(value, 'content_type', None) not in (None, expected_types[extension]):
            raise serializers.ValidationError('File content type does not match its extension.')
        return value


class GrievanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GrievanceHistory
        fields = ('previous_status', 'new_status', 'remarks', 'created_at')


class ActionTakenReportSerializer(serializers.ModelSerializer):
    officer_email = serializers.EmailField(source='officer.email', read_only=True)

    class Meta:
        model = ActionTakenReport
        fields = ('id', 'officer_email', 'report', 'review_status', 'review_remarks', 'created_at')
        read_only_fields = fields


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ('id', 'original_name', 'content_type', 'size', 'uploaded_at', 'download_url')

    def get_download_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(f'/api/v1/grievances/{obj.grievance_id}/attachments/{obj.pk}/') if request else None


class GrievanceSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    history = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    action_reports = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = Grievance
        fields = ('id', 'reference_number', 'district', 'category', 'subject', 'description', 'priority', 'status', 'department', 'department_name', 'created_at', 'updated_at', 'history', 'attachments', 'action_reports', 'assignment', 'feedback')
        read_only_fields = ('id', 'reference_number', 'priority', 'status', 'department', 'created_at', 'updated_at')

    def get_history(self, obj):
        request = self.context.get('request')
        can_read_internal = request and request.user.is_authenticated and request.user.role in ('CMO', 'OFFICER')
        history = obj.history.all() if can_read_internal else obj.history.filter(is_internal=False)
        return GrievanceHistorySerializer(history, many=True).data

    def get_action_reports(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or request.user.role not in ('CMO', 'OFFICER'):
            return []
        reports = obj.action_reports.all()
        if request.user.role == 'OFFICER':
            reports = reports.filter(officer=request.user)
        return ActionTakenReportSerializer(reports.order_by('created_at'), many=True).data

    def get_assignment(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or request.user.role not in ('CMO', 'OFFICER'):
            return None
        assignments = DepartmentAssignment.objects.filter(grievance=obj, is_active=True).select_related('department', 'officer')
        if request.user.role == 'OFFICER':
            assignments = assignments.filter(officer=request.user)
        assignment = assignments.order_by('-assigned_at', '-pk').first()
        if not assignment:
            return None
        return {
            'department_id': assignment.department_id,
            'department_name': assignment.department.name,
            'officer_id': assignment.officer_id,
            'officer_name': assignment.officer.get_full_name() if assignment.officer else '',
            'officer_email': assignment.officer.email if assignment.officer else '',
            'remarks': assignment.remarks,
            'assigned_at': assignment.assigned_at,
        }

    def get_feedback(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or request.user.role != 'CITIZEN' or obj.citizen_id != request.user.pk:
            return None
        try:
            feedback = obj.feedback
        except CitizenFeedback.DoesNotExist:
            return None
        return {'rating': feedback.rating, 'comments': feedback.comments, 'created_at': feedback.created_at}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get('tracking'):
            data.pop('description', None)
            data.pop('attachments', None)
            data.pop('feedback', None)
        return data

    def create(self, validated_data):
        request = self.context['request']
        files = request.FILES.getlist('attachments')
        validated_files = []
        for upload in files:
            item = AttachmentInputSerializer(data={'file': upload})
            item.is_valid(raise_exception=True)
            validated_files.append(item.validated_data['file'])
        with transaction.atomic():
            grievance = Grievance.objects.create(citizen=request.user, **validated_data)
            GrievanceHistory.objects.create(grievance=grievance, new_status=grievance.status, responsible_user=request.user)
            for file in validated_files:
                Attachment.objects.create(grievance=grievance, file=file, original_name=Path(file.name).name, content_type=getattr(file, 'content_type', 'application/octet-stream'), size=file.size)
        return grievance
