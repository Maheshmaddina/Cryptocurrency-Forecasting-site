"""
Vercel entrypoint: serves the CryptoSight Django project as a WSGI app.

vercel.json rewrites every request here. Settings detect Vercel through the
VERCEL environment variable (no Celery, WhiteNoise static files, Postgres via
DATABASE_URL).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'Django'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CryptoSight.settings')

import django  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402

# Migrations are applied on the first request by
# CryptoSight.startup.EnsureMigrationsMiddleware
app = get_wsgi_application()
