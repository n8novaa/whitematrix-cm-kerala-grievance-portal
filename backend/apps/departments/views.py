from rest_framework import generics, permissions
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
