import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.departments.models import Department


def create_reference_number():
    year = timezone.now().year
    return f'CMK-{year}-{secrets.token_hex(4).upper()}'


class Grievance(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        REOPENED = 'REOPENED', 'Reopened'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    reference_number = models.CharField(max_length=20, unique=True, default=create_reference_number, editable=False)
    citizen = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='grievances')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT, related_name='grievances')
    category = models.CharField(max_length=80)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.reference_number


class GrievanceHistory(models.Model):
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='history')
    previous_status = models.CharField(max_length=16, choices=Grievance.Status.choices, blank=True)
    new_status = models.CharField(max_length=16, choices=Grievance.Status.choices)
    responsible_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='grievance_history')
    remarks = models.TextField(blank=True)
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)


def attachment_upload_path(instance, filename):
    return f'grievances/{instance.grievance_id}/{secrets.token_hex(8)}_{filename}'


class Attachment(models.Model):
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=attachment_upload_path)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
