"""
URL routing for cryptocurrency price prediction features
"""
from django.urls import path
from . import views

app_name = 'predict'

urlpatterns = [
    path('selector/', views.selector_view, name='selector'),
    path('processing/', views.processing_view, name='processing'),
    path('results/', views.results_view, name='results'),
    path('api/predict/', views.prediction_api, name='prediction_api'),
    path('api/predict-async/', views.prediction_api_async, name='prediction_api_async'),
    path('api/task-status/', views.task_status_api, name='task_status_api'),
    path('history/', views.prediction_history, name='history'),
]