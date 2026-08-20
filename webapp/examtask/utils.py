from utils.content import get_siblings
from .models import ExamTaskAttempt

def propagate_attempt(attempt_object):
    for page in get_siblings(attempt_object.task, attempt_object.parent, attempt_object.instance):
        try:
            existing = ExamTaskAttempt.objects.get(
                user=attempt_object.user,
                instance=attempt_object.instance,
                parent=attempt_object.parent,
                task=page
            )
            created = False
        except ExamTaskAttempt.DoesNotExist:
            existing = ExamTaskAttempt(
                user=attempt_object.user,
                instance=attempt_object.instance,
                parent=attempt_object.parent,
                task=page
            )
            created = True

        existing.start = attempt_object.start
        existing.end = attempt_object.end
        existing.title = attempt_object.title
        existing.save()
        if created:
            existing.assign_tasks()
