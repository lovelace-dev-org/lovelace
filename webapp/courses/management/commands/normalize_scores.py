from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from courses.models import UserTaskCompletion


class Command(BaseCommand):
    help = "Normalizes scores from an integer to a quotient of the task's default points value"

    def handle(self, *args, **kwargs):
        paginator = Paginator(UserTaskCompletion.objects.all(), 1000)
        counter = 0

        for page in paginator.page_range:
            print(f"Processing page {page} / {paginator.num_pages}")

            for record in paginator.page(page).object_list.iterator():
                if record.points > 1:
                    quotient = record.points / max(record.exercise.default_points, 1)
                    record.points = quotient
                    record.save()
                    counter += 1

        print(f"Updated {counter} evaluation(s)")
