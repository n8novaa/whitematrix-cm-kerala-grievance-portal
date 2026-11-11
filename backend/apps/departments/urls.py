from django.urls import path
from .views import DepartmentDetailView, DepartmentListView, DepartmentOfficersView

urlpatterns = [
    path('', DepartmentListView.as_view(), name='department-list'),
    path('<int:pk>/officers/', DepartmentOfficersView.as_view(), name='department-officers'),
    path('<int:pk>/', DepartmentDetailView.as_view(), name='department-detail'),
]
