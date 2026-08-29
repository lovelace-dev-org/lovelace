from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from courses.models import ContentGraph, CourseInstance


class Command(BaseCommand):
    help = "Regenerates cache for all content in all course instances"

    def add_arguments(self, parser):
        parser.add_argument(
            "--frozen",
            action="store_true",
            help="Regenerate for frozen instances as well",
        )

    def handle(self, *args, **options):
        print("Clearing content tree caches and term caches")
        lang_list = settings.LANGUAGES
        for instance in CourseInstance.objects.all():
            if not options["frozen"] and instance.frozen:
                print(f"Skipping frozen instance {instance}")
                continue

            instance.clear_content_tree_cache
            instance_slug = instance.slug
            for lang, __ in lang_list:
                cache.set(
                    f"termbank_contents_{instance_slug}_{lang}",
                    None,
                    timeout=None,
                )
                cache.set(
                    f"termbank_div_data_{instance_slug}_{lang}",
                    None,
                    timeout=None,
                )

        print("Regenerating content caches")
        if not options["frozen"]:
            cgs = ContentGraph.objects.exclude(instance__frozen=True)
        else:
            cgs = ContentGraph.objects.all()

        for cg in cgs:
            print(f"Regenerating {cg.content.slug} ({cg.instance.slug})")
            cg.content.regenerate_cache(cg.instance)
