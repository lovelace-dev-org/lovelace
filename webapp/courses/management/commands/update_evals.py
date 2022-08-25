import json
from django.core.management.base import BaseCommand, CommandError
from courses.models import Evaluation
from courses.tasks import generate_results

class Command(BaseCommand):
    help = "Updates stored file upload exercise evaluations to new format"
    
    def handle(self, *args, **options):
        counter = 0
        evaluations = Evaluation.objects.exclude(test_results="")
        for ev in evaluations:
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


