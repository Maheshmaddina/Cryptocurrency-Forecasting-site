"""
Applies database migrations on the first request each serverless instance serves.

Vercel has no release step, and every instance starts with a fresh filesystem
(and a newly connected Postgres starts empty), so the schema has to be created
at runtime. Running it at import time proved unreliable, hence the middleware.
"""
import logging
import threading

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_state = {'applied': False, 'error': None}


def migration_state():
    """Snapshot of the last migration attempt, for the health endpoint"""
    return dict(_state)


def ensure_migrations():
    with _lock:
        if _state['applied']:
            return
        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if plan:
                logger.info(f"Applying {len(plan)} pending migrations")
                call_command('migrate', interactive=False, verbosity=0)
            _state['applied'] = True
            _state['error'] = None
        except Exception as exc:
            _state['error'] = f"{type(exc).__name__}: {exc}"
            logger.exception("Applying migrations failed")


class EnsureMigrationsMiddleware:
    """Runs pending migrations once per instance; disabled unless AUTO_MIGRATE"""

    def __init__(self, get_response):
        if not settings.AUTO_MIGRATE:
            raise MiddlewareNotUsed
        self.get_response = get_response

    def __call__(self, request):
        if not _state['applied']:
            ensure_migrations()
        return self.get_response(request)
