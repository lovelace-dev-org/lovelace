from django.core.management.base import BaseCommand, CommandError
from courses.models import ContentGraph

class Command(BaseCommand):
    help = "Regenerates cache for all content in all course instances"
    
    def handle(self, *args, **options):
        for cg in ContentGraph.objects.all():
            cg.content.regenerate_cache(cg.instance)
            