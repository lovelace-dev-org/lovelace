from __future__ import absolute_import

import os

from celery import Celery
#from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lovelace.settings')

from django.conf import settings

app = Celery('lovelace')

# Using a string here means the worker doesn't have to serialize
# the configuration object.
app.config_from_object('django.conf:settings', namespace="CELERY")

# load task modules from all registered Django app configs.
app.autodiscover_tasks(packages=["courses", "teacher_tools", "stats"])
# setting CELERY_ROUTES in settings seems to do nothing, but this works
app.conf.update(
    task_routes = settings.CELERY_ROUTES
)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

#@app.on_after_finalize.connect
#def setup_periodic_tasks(sender, **kwargs):
    #app.conf.beat_schedule = {
        #'ensure-available-repeated-template-exercise-sessions': {
            #'task': 'courses.precache-repeated-template-sessions',
            #'schedule': 5.0, #300.0,
            #'args': (),
            #'options': {'expires': 150.0,}, # We don't need these tasks hanging around
        #},
    #}
