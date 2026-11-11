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


class DepartmentAssignment(models.Model):
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='assignments')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='assignments')
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='grievance_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_assignments')
    remarks = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)


class ActionTakenReport(models.Model):
    class ReviewStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending CMO review'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        RETURNED = 'RETURNED', 'Returned'

    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='action_reports')
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='action_reports')
    report = models.TextField()
    review_status = models.CharField(max_length=12, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    review_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CitizenFeedback(models.Model):
    grievance = models.OneToOneField(Grievance, on_delete=models.CASCADE, related_name='feedback')
    citizen = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='grievance_feedback')
    rating = models.PositiveSmallIntegerField()
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='feedback_rating_1_to_5')]


class ContactEnquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
