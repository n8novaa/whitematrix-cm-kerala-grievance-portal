from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.accounts.models import User
from apps.accounts.permissions import IsCMO
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentListView(generics.ListAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = Department.objects.filter(is_active=True)


class DepartmentDetailView(generics.RetrieveAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = Department.objects.filter(is_active=True)


class DepartmentOfficersView(APIView):
    permission_classes = (IsCMO,)

    def get(self, request, pk):
        department = get_object_or_404(Department, pk=pk, is_active=True)
        officers = User.objects.filter(role=User.Role.OFFICER, department=department, is_active=True).order_by('first_name', 'last_name', 'email')
        return Response([{'id': officer.pk, 'name': officer.get_full_name() or officer.email, 'email': officer.email} for officer in officers])
