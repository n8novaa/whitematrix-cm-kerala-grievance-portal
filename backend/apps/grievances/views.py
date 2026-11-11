from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from .models import Attachment, Grievance
from .serializers import GrievanceSerializer


class CitizenGrievanceListCreateView(generics.ListCreateAPIView):
    serializer_class = GrievanceSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.role != 'CITIZEN':
            raise PermissionDenied('Citizen role required.')
        return Grievance.objects.filter(citizen=self.request.user).select_related('department').prefetch_related('history', 'attachments')


class CitizenGrievanceDetailView(generics.RetrieveAPIView):
    serializer_class = GrievanceSerializer

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
        if request.user.role not in ('CMO', 'OFFICER') and grievance.citizen_id != request.user.pk:
            raise PermissionDenied()
        attachment = get_object_or_404(Attachment, pk=attachment_id, grievance=grievance)
        return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.original_name)
