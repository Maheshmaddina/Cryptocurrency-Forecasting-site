from __future__ import absolute_import, unicode_literals
import os
import logging
from celery import Celery
from celery.signals import worker_ready

# Set the default Django settings module for 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CryptoSight.settings')

# Create Celery app
app = Celery('CryptoSight')

# Load settings from Django settings, using CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks inside installed apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')


# Warm-up hook: preload and prime ML models so first task is fast
@worker_ready.connect
def warmup_models(sender=None, **kwargs):
    logger = logging.getLogger(__name__)
    try:
        # Import here to avoid import overhead in Django process startup
        from predict.prediction import load_model_and_scaler, get_live_prediction

        symbols_to_prime = ["BTC"]
        intervals_to_prime = ["1h", "1d"]

        for symbol in symbols_to_prime:
            for interval in intervals_to_prime:
                model, scaler = load_model_and_scaler(symbol, interval)
                if model is None or scaler is None:
                    continue
                # Run a tiny forward-pass to prime TF runtime and caches
                try:
                    _ = get_live_prediction(symbol, interval, steps_ahead=1, usd_to_inr=float(os.environ.get('USD_TO_INR', '88.75')))
                except Exception:
                    # Prediction priming can fail if network is offline; that's fine
                    pass
        logger.info("Celery warm-up complete: models preloaded")
    except Exception as exc:
        logger.warning(f"Celery warm-up skipped: {exc}")
