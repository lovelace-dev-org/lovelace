import json
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from courses.models import Evaluation
from courses.tasks import generate_results


class Command(BaseCommand):
    help = "Updates stored file upload exercise evaluations to new format"

    def handle(self, *args, **options):
        paginator = Paginator(Evaluation.objects.all(), 200)
        counter = 0

        for page in paginator.page_range:
            print(f"Processing page {page} / {paginator.num_pages}")

            for ev in paginator.page(page).object_list.iterator():
                try:
                    jsonres = json.loads(ev.test_results)
                    res = generate_results(jsonres)
                except Exception as e:
                    pass
                else:
                    ev.test_results = json.dumps(res)
                    ev.save()
                    counter += 1

        print(f"Updated {counter} evaluation(s)")
