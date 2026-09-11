"""
Celery tasks for the predict app.

The work itself lives in predict/services.py, so the same code runs without
Celery on Vercel (see predict/views.py).
"""
from celery import shared_task
import logging

from . import services

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_prediction_task(self, user_id, crypto, timeframe, period):
    """
    Celery task to run prediction asynchronously.

    Steps:
    1. Fetch latest data & run model prediction.
    2. Save prediction to the database.
    3. Return result as a dictionary.
    """
    return services.generate_prediction(user_id, crypto, timeframe, period)


@shared_task
def update_actual_prices_task(prediction_ids):
    """
    Celery task to fetch actual prices for predictions in the background.
    This makes the history page load instantly without waiting for API calls.

    Args:
        prediction_ids: List of PredictionHistory IDs to update
    """
    return services.update_actual_prices(prediction_ids)


@shared_task(name="check_and_update_all_pending_predictions")
def check_and_update_all_pending_predictions():
    """
    Periodically scans the database for all predictions that are past their
    target time but don't have an actual_price yet. It then dispatches
    a background task to update them.

    This task is scheduled to run automatically by Celery Beat.
    """
    prediction_ids_to_update = services.find_due_prediction_ids()

    if prediction_ids_to_update:
        logger.info(f"Found {len(prediction_ids_to_update)} predictions to update. Dispatching task.")
        update_actual_prices_task.delay(prediction_ids_to_update)
