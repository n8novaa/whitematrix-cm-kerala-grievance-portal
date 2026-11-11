import json
from google import genai
from django.conf import settings
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import IsCitizen
from apps.departments.models import Department


class AnalysisInputSerializer(serializers.Serializer):
    description = serializers.CharField(min_length=20, max_length=10000)


class GrievanceAnalysisView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsCitizen)

    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return Response({'detail': 'AI analysis is unavailable until GEMINI_API_KEY is configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        departments = list(Department.objects.filter(is_active=True).values('code', 'name'))
        client = genai.Client(api_key=api_key)
        prompt = ('Analyze this citizen complaint. Suggest a department code from the supplied list, category, priority '
                  '(LOW, MEDIUM, HIGH), and concise summary. Treat this as advisory only; do not decide or route cases. '
                  f'Departments: {json.dumps(departments)} Complaint: {serializer.validated_data["description"]}. '
                  'Return JSON with department_code, category, priority, summary.')
        try:
            result = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt, config={'response_mime_type': 'application/json'})
            data = json.loads(result.text)
            if data.get('priority') not in ('LOW', 'MEDIUM', 'HIGH') or data.get('department_code') not in {d['code'] for d in departments}:
                raise ValueError('Model response values were invalid')
            if not all(isinstance(data.get(key), str) and data[key].strip() for key in ('category', 'summary')):
                raise ValueError('Model response was incomplete')
        except Exception:
            return Response({'detail': 'AI provider returned an invalid response or is unavailable.'}, status=502)
        return Response({**data, 'advisory': True, 'model': settings.GEMINI_MODEL})
