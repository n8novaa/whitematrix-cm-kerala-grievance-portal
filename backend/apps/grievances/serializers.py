from pathlib import Path
from django.db import transaction
from rest_framework import serializers
from .models import Attachment, Grievance, GrievanceHistory

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

    class Meta:
        model = Grievance
        fields = ('id', 'reference_number', 'category', 'subject', 'description', 'priority', 'status', 'department', 'department_name', 'created_at', 'updated_at', 'history', 'attachments')
        read_only_fields = ('id', 'reference_number', 'priority', 'status', 'department', 'created_at', 'updated_at')

    def get_history(self, obj):
        history = obj.history.filter(is_internal=False)
        return GrievanceHistorySerializer(history, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get('tracking'):
            data.pop('description', None)
            data.pop('attachments', None)
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
