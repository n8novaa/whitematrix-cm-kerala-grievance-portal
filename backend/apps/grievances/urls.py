from django.urls import path
from .views import (AttachmentDownloadView, AssignGrievanceView, CitizenGrievanceDetailView,
    CitizenGrievanceListCreateView, CMOGrievanceQueueView, CMOResolveView,
    OfficerQueueView, OfficerProgressUpdateView, SubmitActionReportView, TrackGrievanceView, CMOReportReviewView,
    CitizenReopenView, CitizenFeedbackView, ContactEnquiryView)

urlpatterns = [
    path('', CitizenGrievanceListCreateView.as_view(), name='grievance-list-create'),
    path('track/<str:reference_number>/', TrackGrievanceView.as_view(), name='grievance-track'),
    path('<int:pk>/', CitizenGrievanceDetailView.as_view(), name='grievance-detail'),
    path('<int:grievance_id>/attachments/<int:attachment_id>/', AttachmentDownloadView.as_view(), name='grievance-attachment'),
    path('cmo/queue/', CMOGrievanceQueueView.as_view(), name='cmo-grievance-queue'),
    path('<int:pk>/assign/', AssignGrievanceView.as_view(), name='grievance-assign'),
    path('officer/queue/', OfficerQueueView.as_view(), name='officer-grievance-queue'),
    path('<int:pk>/action-reports/', SubmitActionReportView.as_view(), name='action-report-submit'),
    path('<int:pk>/updates/', OfficerProgressUpdateView.as_view(), name='officer-progress-update'),
    path('<int:pk>/resolve/', CMOResolveView.as_view(), name='grievance-resolve'),
    path('action-reports/<int:report_id>/review/', CMOReportReviewView.as_view(), name='action-report-review'),
    path('<int:pk>/reopen/', CitizenReopenView.as_view(), name='grievance-reopen'),
    path('<int:pk>/feedback/', CitizenFeedbackView.as_view(), name='grievance-feedback'),
    path('contact-enquiries/', ContactEnquiryView.as_view(), name='contact-enquiry'),
]
