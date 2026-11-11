from django.urls import path
from .views import DepartmentDetailView, DepartmentListView

urlpatterns = [
    path('', DepartmentListView.as_view(), name='department-list'),
    path('<int:pk>/', DepartmentDetailView.as_view(), name='department-detail'),
]
