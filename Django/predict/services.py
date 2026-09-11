"""
Prediction jobs as plain functions.

Locally they run inside Celery tasks (predict/tasks.py). On Vercel, where there
is no Celery worker or Redis, the views and the cron endpoint call them directly.
"""
import logging
import os
import traceback
from datetime import timedelta, timezone as dt_timezone

from django.contrib.auth.models import User
from django.utils import timezone

from .models import PredictionHistory
from .prediction import binance_get

logger = logging.getLogger(__name__)


def generate_prediction(user_id, crypto, timeframe, period):
    """
    Fetch latest data & run the model, save the prediction to the user's
    history (user_id 0 = anonymous) and return the result dictionary.
    """
    from .views import get_prediction  # views imports this module

    try:
        logger.info(f"🚀 Prediction started: {crypto} | {timeframe} | {period} | user_id={user_id}")

        prediction_data = get_prediction(crypto, timeframe, int(period))

        if user_id > 0:
            user = User.objects.filter(id=user_id).first()
            if user:
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
                    prediction_target_time=target_time,
                )
                logger.info(f"✅ Prediction saved in DB (ID: {history_entry.id})")
        else:
            logger.info("ℹ️  Anonymous user - prediction not saved to history")

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
            'volatility': prediction_data.get('volatility', 'Medium'),
        }

    except Exception as e:
        logger.error(f"❌ Prediction error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': str(e)}


def find_due_prediction_ids(queryset=None):
    """
    Return IDs of predictions whose target candle has closed but that have no
    actual price yet. Also backfills missing target times on old predictions.
    """
    if queryset is None:
        queryset = PredictionHistory.objects.all()

    # --- Self-healing step: Fix old predictions with missing target times ---
    predictions_to_fix = queryset.filter(prediction_target_time__isnull=True)
    fix_count = predictions_to_fix.count()
    if fix_count > 0:
        logger.info(f"Found {fix_count} historical predictions with missing target times. Backfilling now...")
        for prediction in predictions_to_fix:
            time_delta = timedelta(
                hours=prediction.period if prediction.timeframe == 'hourly' else prediction.period * 24
            )
            prediction.prediction_target_time = prediction.created_at + time_delta
            prediction.save(update_fields=['prediction_target_time'])
        logger.info(f"✅ Successfully backfilled target times for {fix_count} predictions.")

    pending_predictions = queryset.filter(actual_price__isnull=True, prediction_target_time__isnull=False)

    due_ids = []
    now = timezone.now()
    for prediction in pending_predictions:
        # The 'safe' time is when the candlestick containing the target time has closed
        target_time = prediction.prediction_target_time
        if prediction.timeframe == 'hourly':
            # e.g., a 17:52 target is in the 17:00-18:00 candle, which closes at 18:00
            safe_update_time = target_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            # Daily candles close at the start of the next day in UTC
            target_time_utc = target_time.astimezone(dt_timezone.utc)
            safe_update_time = target_time_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        if now >= safe_update_time:
            due_ids.append(prediction.id)

    return due_ids


def update_actual_prices(prediction_ids):
    """Fetch the actual closing price at each prediction's target time from Binance."""
    logger.info(f"🔄 Updating {len(prediction_ids)} actual prices")

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

            # Fetch the kline that CONTAINS the target time. Binance works in UTC.
            symbol = f"{prediction.crypto}USDT"
            interval = "1h" if prediction.timeframe == 'hourly' else "1d"
            target_dt = prediction.prediction_target_time.astimezone(dt_timezone.utc)
            if interval == "1h":
                start_dt = target_dt.replace(minute=0, second=0, microsecond=0)
            else:
                start_dt = target_dt.replace(hour=0, minute=0, second=0, microsecond=0)

            start_timestamp_ms = int(start_dt.timestamp() * 1000)
            data = binance_get("/api/v3/klines", {
                "symbol": symbol, "interval": interval, "startTime": start_timestamp_ms, "limit": 1,
            })

            if data:
                # The kline's close is the price at the END of that interval,
                # the most accurate available price for our target time
                close_price_usd = float(data[0][4])
                price_inr = close_price_usd * usd_to_inr

                prediction.actual_price = round(price_inr, 2)
                prediction.save(update_fields=['actual_price'])

                updated_count += 1
                target_time_str = prediction.prediction_target_time.strftime('%Y-%m-%d %H:%M')
                logger.info(f"✅ Updated actual price for {prediction.crypto} (ID: {pred_id}) at {target_time_str}: ₹{price_inr:.2f}")
            else:
                logger.warning(f"⚠️ No historical data from Binance for {prediction.crypto} (ID: {pred_id}) at timestamp {start_timestamp_ms}")

        except PredictionHistory.DoesNotExist:
            logger.error(f"❌ Prediction ID {pred_id} not found")
        except Exception as e:
            logger.error(f"❌ Error updating prediction ID {pred_id}: {str(e)}")
            continue

    logger.info(f"📊 Updated {updated_count}/{len(prediction_ids)} actual prices")
    return {'updated': updated_count, 'total': len(prediction_ids)}
