from django.core.management.base import BaseCommand, CommandError
from courses.models import CourseInstance, EmbeddedLink, User, UserAnswer, UserTaskCompletion
from routine_exercise.models import RoutineExerciseProgress
from reversion.models import Version
from utils.content import get_course_instance_tasks
from teacher_tools.utils import check_user_completion

class Command(BaseCommand):
    help = "Generates initial task completion instances. This will take a while."
    
    def handle(self, *args, **options):
        for instance in CourseInstance.objects.all():
            print("Instance:", instance.slug)
            instance_tasks = EmbeddedLink.objects.filter(instance=instance).order_by("embedded_page__name")
            users = User.objects.all()
            n = users.count()
            print("Users ({}):".format(n), end="")
            for user in users:
                user_results = self._get_results(user, instance_tasks, instance)
                for slug, result in user_results.items():
                    try:
                        completion = UserTaskCompletion.objects.get(
                            exercise=result["eo"],
                            instance=instance,
                            user=user
                        )
                    except UserTaskCompletion.DoesNotExist:
                        completion = UserTaskCompletion(
                            exercise=result["eo"],
                            instance=instance,
                            user=user,
                            state=result["result"]
                        )
                        completion.save()
                print(".", end="", flush=True)
            print()
                            
    def _get_results(self, user, task_links, instance):
        results = {}
        course = instance.course
        for link in task_links:
            exercise_obj = link.embedded_page.get_type_object()
            if link.revision is not None:
                exercise_obj = Version.objects.get_for_object(exercise_obj).get(revision=link.revision)._object_version.object
                
            if exercise_obj.content_type == "ROUTINE_EXERCISE":
                try:
                    progress = RoutineExerciseProgress.objects.get(
                        user=user,
                        exercise=exercise_obj,
                        instance=instance
                    )
                except RoutineExerciseProgress.DoesNotExist:
                    pass
                else:
                    if progress.completed:
                        results[exercise_obj.slug] = {
                            "eo": exercise_obj,
                            "result": "correct"
                        }
                    else:
                        results[exercise_obj.slug] = {
                            "eo": exercise_obj,
                            "result": "incorrect"
                        }
            else:
                answers = UserAnswer.get_task_answers(exercise_obj, instance=instance, user=user)
                if answers.filter(evaluation__correct=True).count():
                    results[exercise_obj.slug] = {
                        "eo": exercise_obj,
                        "result": "correct"
                    }
                    if exercise_obj.evaluation_group:
                        group = self._get_group(task_links, exercise_obj)
                        for task in group:
                            if task.slug in results and results[task.slug]["result"] != "correct":
                                results[task.slug]["result"] = "credited"
                            else:
                                results[task.slug] = {
                                    "eo": task,
                                    "result": "credited"
                                }
                elif answers.count():
                    results[exercise_obj.slug] = {
                        "eo": exercise_obj,
                        "result": "incorrect"
                    }
        return results
                
    def _get_group(self, task_links, task):
        group_links = task_links.filter(
            embedded_page__evaluation_group=task.evaluation_group
        ).exclude(
            embedded_page__id=task.id
        )
        return [link.embedded_page.get_type_object() for link in group_links]

