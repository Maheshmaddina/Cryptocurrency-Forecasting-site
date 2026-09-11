"""Django app configuration for authuser app"""
from django.apps import AppConfig


class AuthuserConfig(AppConfig):
    """Configuration for user authentication and profile management app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authuser'
