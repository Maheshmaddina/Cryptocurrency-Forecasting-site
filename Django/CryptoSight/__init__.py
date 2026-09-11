try:
    from .celery import app as celery_app
except ImportError:  # Celery isn't installed in the Vercel deployment
    celery_app = None

__all__ = ('celery_app',)
