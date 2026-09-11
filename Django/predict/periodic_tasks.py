"""
Celery-beat periodic tasks for the predict app.
"""
from celery import shared_task
from datetime import timedelta
from django.utils import timezone
import logging

from .models import PredictionHistory
from .tasks import update_actual_prices_task

logger = logging.getLogger(__name__)

@shared_task(name="check_and_update_all_pending_predictions")
def check_and_update_all_pending_predictions():
    """
    Periodically scans the database for all predictions that are past their
    target time but don't have an actual_price yet. It then dispatches
    a background task to update them.
    
    This task is scheduled to run automatically by Celery Beat.
    """
    # --- Self-healing step: Fix old predictions with missing target times ---
    predictions_to_fix = PredictionHistory.objects.filter(prediction_target_time__isnull=True)
    fix_count = predictions_to_fix.count()
    
    if fix_count > 0:
        logger.info(f"Found {fix_count} historical predictions with missing target times. Backfilling now...")
        for prediction in predictions_to_fix:
            # Calculate the correct target time based on when the prediction was created
            time_delta = timedelta(
                hours=prediction.period if prediction.timeframe == 'hourly' else prediction.period * 24
            )
            correct_target_time = prediction.created_at + time_delta
            prediction.prediction_target_time = correct_target_time
            prediction.save(update_fields=['prediction_target_time'])
        logger.info(f"✅ Successfully backfilled target times for {fix_count} predictions.")
    # --- End of self-healing step ---


    # --- Original logic: Find due predictions and dispatch update task ---
    pending_predictions = PredictionHistory.objects.filter(
        actual_price__isnull=True,
        prediction_target_time__lte=timezone.now()
    )
    
    prediction_ids_to_update = list(pending_predictions.values_list('id', flat=True))
    
    if prediction_ids_to_update:
        logger.info(f"Found {len(prediction_ids_to_update)} predictions to update. Dispatching task.")
        update_actual_prices_task.delay(prediction_ids_to_update)