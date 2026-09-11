"""
Django admin configuration for prediction history management
"""
from django.contrib import admin
from .models import PredictionHistory

@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    """Admin interface for viewing and managing prediction history records"""
    list_display = ['user', 'crypto', 'timeframe', 'current_price', 'predicted_price', 'created_at']
    list_filter = ['crypto', 'timeframe', 'market_sentiment', 'created_at']
    search_fields = ['user__username', 'crypto']
    readonly_fields = ['created_at']
