import os

import lovelace.celery
from celery.result import AsyncResult

from time import sleep

os.environ['DJANGO_SETTINGS_MODULE'] = 'lovelace.settings'

from courses.models import UserFileTaskAnswer

task_id = "098732ec-d2f9-4bc2-8166-e34e5622ed0b"

async_result = AsyncResult(task_id)
print(async_result.get(no_ack=True))

sleep(2)

as_res2 = AsyncResult(task_id)
print(as_res2.get(no_ack=False))

print(async_result is as_res2)

# Detect whether a task has been given an evaluation
#if userfiletaskanswer.evaluation.correct is None


# parent tasks have been mentioned in the docs
# -> probably _one_ task id will suffice!
