from django.core.management.base import BaseCommand
from routine_exercise.models import RoutineExerciseProgress

class Command(BaseCommand):
    help = "Generates score and max score values for existing progress objects based on the task's defaults"

    def handle(self, *args, **options):
        n = RoutineExerciseProgress.objects.count()

        for i, progress in enumerate(RoutineExerciseProgress.objects.all(), start=1):
            if progress.completed and progress.points == 0:
                progress.points = progress.exercise.default_points
                progress.max_points = progress.exercise.default_points
                progress.save()

            print(f"\r{i} / {n}", end="")
        print()




