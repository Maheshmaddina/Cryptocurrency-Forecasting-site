"""
Health endpoint (/healthz/) for checking a deployment from outside.

Reports whether the database is reachable and migrated. It deliberately exposes
no credentials - no host, user or password, only the backend name.
"""
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse

from .startup import migration_state


def healthz(request):
    status = {
        'on_vercel': settings.ON_VERCEL,
        'use_celery': settings.USE_CELERY,
        'database_url_set': bool(settings.DATABASE_URL),
        'db_backend': settings.DATABASES['default']['ENGINE'].rsplit('.', 1)[-1],
    }

    try:
        connection.ensure_connection()
        status['db_connected'] = True
    except Exception as exc:
        status['db_connected'] = False
        status['db_error'] = f"{type(exc).__name__}: {exc}"
        return JsonResponse(status, status=500)

    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        status['unapplied_migrations'] = len(plan)
        status['user_table_exists'] = 'auth_user' in connection.introspection.table_names()
        status['migrations'] = migration_state()
    except Exception as exc:
        status['migration_error'] = f"{type(exc).__name__}: {exc}"
        return JsonResponse(status, status=500)

    return JsonResponse(status)
