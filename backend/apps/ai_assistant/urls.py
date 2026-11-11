from django.urls import path
from .views import GrievanceAnalysisView

urlpatterns = [path('analyze/', GrievanceAnalysisView.as_view(), name='grievance-analysis')]
