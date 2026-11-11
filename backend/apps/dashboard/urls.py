from django.urls import path
from .views import CMOStatisticsView

urlpatterns = [path('cmo/statistics/', CMOStatisticsView.as_view(), name='cmo-statistics')]
