"""Django app configuration for predict app"""
from django.apps import AppConfig


class PredictConfig(AppConfig):
    """Configuration for cryptocurrency price prediction app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predict'
