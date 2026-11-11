from django.db.models import Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import IsCMO
from apps.grievances.models import Grievance


class CMOStatisticsView(APIView):
    permission_classes = (IsAuthenticated, IsCMO)

    def get(self, request):
        qs = Grievance.objects.all()
        return Response({
            'total': qs.count(),
            'pending': qs.exclude(status=Grievance.Status.RESOLVED).count(),
            'resolved': qs.filter(status=Grievance.Status.RESOLVED).count(),
            'overdue': qs.filter(created_at__lt=timezone.now() - timezone.timedelta(days=7)).exclude(status=Grievance.Status.RESOLVED).count(),
            'by_department': list(qs.values('department__name').annotate(count=Count('id')).order_by('department__name')),
            'by_district': list(qs.values('district').annotate(count=Count('id')).order_by('district')),
            'by_status': list(qs.values('status').annotate(count=Count('id')).order_by('status')),
        })
