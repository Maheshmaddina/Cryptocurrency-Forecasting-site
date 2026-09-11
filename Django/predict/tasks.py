from celery import shared_task
from django.conf import settings
from .views import get_prediction
from .models import PredictionHistory
import os
import logging
import requests
from django.utils import timezone
from datetime import datetime, timedelta

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
    from django.contrib.auth.models import User

    try:
        logger.info(f"\n🚀 Celery Task Started: {crypto} | {timeframe} | {period} | user_id={user_id}")
        print(f"\n🚀 Celery Task Started: {crypto} | {timeframe} | {period} | user_id={user_id}")
        usd_to_inr = float(os.environ.get('USD_TO_INR', '88.75'))
        logger.info(f"💱 USD to INR (env): {usd_to_inr}")
        print(f"💱 USD to INR (env): {usd_to_inr}")

        # Run prediction logic from views.py
        prediction_data = get_prediction(crypto, timeframe, int(period))

        # If user exists and is authenticated, store result in PredictionHistory
        if user_id > 0:
            user = User.objects.filter(id=user_id).first()
            if user:
                # Calculate the target time for the prediction
                target_time = timezone.now() + timedelta(
                    hours=period if timeframe == 'hourly' else period * 24
                )
                
                history_entry = PredictionHistory.objects.create(
                    user=user,
                    crypto=crypto,
                    timeframe=timeframe,
                    period=period,
                    current_price=prediction_data['current_price'],
                    predicted_price=prediction_data['predicted_price'],
                    confidence_level=prediction_data['confidence_level'],
                    market_sentiment=prediction_data['market_sentiment'],
                    prediction_target_time=target_time  # <-- Add this line
                )
                logger.info(f"✅ Prediction saved in DB (ID: {history_entry.id})")
                print(f"✅ Prediction saved in DB (ID: {history_entry.id})")
        else:
            logger.info(f"ℹ️  Anonymous user - prediction not saved to history")
            print(f"ℹ️  Anonymous user - prediction not saved to history")

        logger.info("🎯 Celery task completed successfully!")
        print("🎯 Celery task completed successfully!")
        # Return the complete prediction data including chart arrays
        return {
            'status': 'success',
            'crypto': prediction_data['crypto'],
            'timeframe': prediction_data['timeframe'],
            'period': prediction_data['period'],
            'current_price': prediction_data['current_price'],
            'predicted_price': prediction_data['predicted_price'],
            'confidence_level': prediction_data['confidence_level'],
            'market_sentiment': prediction_data['market_sentiment'],
            'timestamps': prediction_data['timestamps'],
            'historical_prices': prediction_data['historical_prices'],
            'predicted_prices': prediction_data['predicted_prices'],
            'min_price': prediction_data.get('min_price', prediction_data['predicted_price'] * 0.95),
            'max_price': prediction_data.get('max_price', prediction_data['predicted_price'] * 1.05),
            'volatility': prediction_data.get('volatility', 'Medium')
        }

    except Exception as e:
        logger.error(f"❌ Error in Celery Task: {str(e)}")
        print(f"❌ Error in Celery Task: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': str(e)}


@shared_task
def update_actual_prices_task(prediction_ids):
    """
    Celery task to fetch actual prices for predictions in the background.
    This makes the history page load instantly without waiting for API calls.
    
    Args:
        prediction_ids: List of PredictionHistory IDs to update
    """
    logger.info(f"🔄 Starting background task to update {len(prediction_ids)} actual prices")
    
    usd_to_inr = float(os.environ.get('USD_TO_INR', '88.75'))
    updated_count = 0
    
    for pred_id in prediction_ids:
        try:
            prediction = PredictionHistory.objects.get(id=pred_id)
            
            # Skip if actual price already exists
            if prediction.actual_price:
                continue
            
            # Check if target time has been reached
            if not prediction.is_prediction_time_reached():
                continue
            
            # To get the price at the target time, we need to find the candlestick
            # that CONTAINS our target time. We do this by fetching the kline
            # that starts just before our target time.
            symbol = f"{prediction.crypto}USDT"
            interval = "1h" if prediction.timeframe == 'hourly' else "1d"
            
            # Round down the target time to the start of the hour/day
            # CRITICAL FIX: Convert target time to UTC before calculations to match Binance API's timezone.
            target_dt_utc = prediction.prediction_target_time.astimezone(timezone.utc)
            
            target_dt = target_dt_utc
            if interval == "1h":
                start_dt = target_dt.replace(minute=0, second=0, microsecond=0)
            else: # "1d"
                start_dt = target_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            
            start_timestamp_ms = int(start_dt.timestamp() * 1000)
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_timestamp_ms}&limit=1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    close_price_usd = float(data[0][4])
                    # The 'close' price of the kline is the price at the END of that interval.
                    # This is the most accurate available price for our target time.
                    
                    price_inr = close_price_usd * usd_to_inr
                    
                    prediction.actual_price = round(price_inr, 2)
                    prediction.save(update_fields=['actual_price'])
                    
                    updated_count += 1
                    target_time_str = prediction.prediction_target_time.strftime('%Y-%m-%d %H:%M')
                    logger.info(f"✅ Updated actual price for {prediction.crypto} (ID: {pred_id}) at {target_time_str}: ₹{price_inr:.2f}")
                else:
                    logger.warning(f"⚠️ No historical data from Binance for {prediction.crypto} (ID: {pred_id}) at timestamp {start_timestamp_ms}")
            else:
                logger.warning(f"⚠️ Binance API failed for {prediction.crypto} (ID: {pred_id}) - Status: {response.status_code}, Response: {response.text}")
                
        except PredictionHistory.DoesNotExist:
            logger.error(f"❌ Prediction ID {pred_id} not found")
        except Exception as e:
            logger.error(f"❌ Error updating prediction ID {pred_id}: {str(e)}")
            continue
    
    logger.info(f"📊 Background task completed: Updated {updated_count}/{len(prediction_ids)} actual prices")
    return {'updated': updated_count, 'total': len(prediction_ids)}


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
    # Find predictions where the actual price is not yet set.
    pending_predictions = PredictionHistory.objects.filter(actual_price__isnull=True)
    
    prediction_ids_to_update = []
    now = timezone.now()

    for prediction in pending_predictions:
        if not prediction.prediction_target_time:
            continue

        # **CRITICAL FIX**: Determine the 'safe' time to fetch the actual price.
        # This is the time when the candlestick containing the target time has *closed*.
        target_time = prediction.prediction_target_time
        
        if prediction.timeframe == 'hourly':
            # For hourly, the candle closes at the start of the NEXT hour.
            # e.g., a 17:52 target is in the 17:00-18:00 candle, which closes at 18:00.
            safe_update_time = target_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else: # 'daily'
            # For daily, the candle closes at the start of the NEXT day (in UTC).
            # We convert to UTC for this calculation to align with Binance's daily candle close.
            target_time_utc = target_time.astimezone(timezone.utc)
            safe_update_time = (target_time_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))

        if now >= safe_update_time:
            prediction_ids_to_update.append(prediction.id)

    if prediction_ids_to_update:
        logger.info(f"Found {len(prediction_ids_to_update)} predictions to update. Dispatching task.")
        update_actual_prices_task.delay(prediction_ids_to_update)
