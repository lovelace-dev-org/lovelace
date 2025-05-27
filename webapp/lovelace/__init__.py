from __future__ import absolute_import
from collections import defaultdict
from django.conf import settings


# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
if settings.ENABLE_CELERY:
    from .celery import app as celery_app
    __all__ = ["celery_app"]

plugins = defaultdict(set)

def register_plugin(module, tags):
    for tag in tags:
        plugins[tag].add(module)

