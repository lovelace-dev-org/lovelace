from django.core.management.base import BaseCommand
from courses.models import ContentGraph


class Command(BaseCommand):
    help = "Regenerates cache for all content in all course instances"

    def add_arguments(self, parser):
        parser.add_argument(
            "--frozen",
            action="store_true",
            help="Regenerate for frozen instances as well",
        )

    def handle(self, *args, **options):
        for cg in ContentGraph.objects.all():
            if not options["frozen"] and cg.instance.frozen:
                print(f"Skipping for frozen instance {cg.instance}")
                continue
            cg.content.regenerate_cache(cg.instance)
