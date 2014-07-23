# Celery tasks
from __future__ import absolute_import

from celery import shared_task

from time import sleep

@shared_task(name="stats.generate-stats")
def generate_stats(something):
    return "Lorem ipsum here be statistics"
