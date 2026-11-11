from django.urls import path
from .views import AttachmentDownloadView, CitizenGrievanceDetailView, CitizenGrievanceListCreateView, TrackGrievanceView

urlpatterns = [
    path('', CitizenGrievanceListCreateView.as_view(), name='grievance-list-create'),
    path('track/<str:reference_number>/', TrackGrievanceView.as_view(), name='grievance-track'),
    path('<int:pk>/', CitizenGrievanceDetailView.as_view(), name='grievance-detail'),
    path('<int:grievance_id>/attachments/<int:attachment_id>/', AttachmentDownloadView.as_view(), name='grievance-attachment'),
]
