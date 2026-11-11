import json
import hashlib
from django.core import signing
from django.shortcuts import get_object_or_404
from django.db import transaction
from google import genai
from django.conf import settings
from rest_framework import permissions, serializers, status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import IsCitizen
from apps.departments.models import Department
from apps.grievances.models import AIRecommendation, Grievance


class AnalysisInputSerializer(serializers.Serializer):
    description = serializers.CharField(min_length=20, max_length=10000)
    grievance_id = serializers.IntegerField(required=False)


class GrievanceAnalysisView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsCitizen)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'ai_analysis'

    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grievance_id = serializer.validated_data.get('grievance_id')
        if grievance_id:
            grievance = get_object_or_404(Grievance, pk=grievance_id, citizen=request.user)
            if grievance.description != serializer.validated_data['description']:
                return Response({'detail': 'Analysis text must match the grievance description.'}, status=400)
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return Response({'detail': 'AI analysis is unavailable until GEMINI_API_KEY is configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        departments = list(Department.objects.filter(is_active=True).values('code', 'name'))
        prompt = ('Analyze this citizen complaint. Suggest a department code from the supplied list, category, priority '
                  '(LOW, MEDIUM, HIGH), and concise summary. Treat this as advisory only; do not decide or route cases. '
                  f'Departments: {json.dumps(departments)} Complaint: {serializer.validated_data["description"]}. '
                  'Return JSON with department_code, category, priority, summary.')
        try:
            client = genai.Client(api_key=api_key, http_options={'timeout': 10000})
            result = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt, config={'response_mime_type': 'application/json'})
            data = json.loads(result.text)
            if data.get('priority') not in ('LOW', 'MEDIUM', 'HIGH') or data.get('department_code') not in {d['code'] for d in departments}:
                raise ValueError('Model response values were invalid')
            if not all(isinstance(data.get(key), str) and data[key].strip() for key in ('category', 'summary')):
                raise ValueError('Model response was incomplete')
            data['category'] = data['category'].strip()[:80]
            data['summary'] = data['summary'].strip()[:500]
        except Exception:
            return Response({'detail': 'AI provider returned an invalid response or is unavailable.'}, status=502)
        if grievance_id:
            with transaction.atomic():
                grievance = get_object_or_404(Grievance.objects.select_for_update(), pk=grievance_id, citizen=request.user)
                recommendation_department = get_object_or_404(Department, code=data['department_code'], is_active=True)
                AIRecommendation.objects.update_or_create(
                    grievance=grievance,
                    defaults={'department': recommendation_department, 'category': data['category'], 'priority': data['priority'], 'summary': data['summary'], 'decision': AIRecommendation.Decision.PENDING, 'reviewed_by': None, 'reviewed_at': None},
                )
        payload = {'description_hash': hashlib.sha256(serializer.validated_data['description'].encode()).hexdigest(), **data}
        token = signing.dumps(payload, salt='grievance-ai-recommendation')
        return Response({**data, 'advisory': True, 'model': settings.GEMINI_MODEL, 'recommendation_token': token})
