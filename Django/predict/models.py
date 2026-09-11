"""
Database models for cryptocurrency price prediction app
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class PredictionHistory(models.Model):
    """Database model for storing cryptocurrency price prediction history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    crypto = models.CharField(max_length=10)  # Cryptocurrency symbol (BTC, ETH, etc.)
    timeframe = models.CharField(max_length=10)  # Prediction timeframe (hourly or daily)
    period = models.IntegerField()  # Number of time periods predicted
    
    current_price = models.DecimalField(max_digits=15, decimal_places=2)
    predicted_price = models.DecimalField(max_digits=15, decimal_places=2)
    confidence_level = models.IntegerField()
    market_sentiment = models.CharField(max_length=20)
    
    created_at = models.DateTimeField(auto_now_add=True)
    prediction_target_time = models.DateTimeField(null=True, blank=True)  # When the prediction was for
    actual_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Prediction Histories'
    
    def __str__(self):
        return f"{self.user.username} - {self.crypto} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def price_change_percentage(self):
        """Calculate percentage change between current and predicted price"""
        if self.current_price > 0:
            return ((self.predicted_price - self.current_price) / self.current_price) * 100
        return 0

    def is_prediction_time_reached(self):
        """Check if the target time for the prediction has been reached"""
        return self.prediction_target_time and timezone.now() >= self.prediction_target_time

    @property
    def prediction_accuracy(self):
        """
        Calculate prediction accuracy as a percentage.
        Returns None if actual price is not available.
        Accuracy = 100 - |(Actual - Predicted) / Actual| * 100
        """
        if self.actual_price is None or self.actual_price == 0:
            return None
        
        error_margin = abs((self.actual_price - self.predicted_price) / self.actual_price)
        accuracy = 100 * (1 - error_margin)
        
        # Clamp accuracy between 0 and 100
        return round(max(0, min(100, accuracy)), 2)
