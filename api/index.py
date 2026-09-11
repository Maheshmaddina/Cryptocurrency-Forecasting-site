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
from django.core.management import call_command  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402

django.setup()

# Serverless instances start fresh, so make sure the schema exists
# (a no-op once the database is up to date)
try:
    call_command('migrate', interactive=False, verbosity=0)
except Exception as exc:
    import traceback

    print(f"[ERROR] migrate on cold start failed: {type(exc).__name__}: {exc}")
    traceback.print_exc()

app = get_wsgi_application()
