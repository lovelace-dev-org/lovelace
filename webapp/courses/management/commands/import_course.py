from zipfile import ZipFile
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from utils.data import import_from_zip

class Command(BaseCommand):
    help = "Imports course content from a zip file"

    def add_arguments(self, parser):
        parser.add_argument(
            "zipfile",
            help="Path of the zip file to be used as the import source"
        )
        parser.add_argument(
            "--responsible",
            help="Username of an existing user to be set as the responsible teacher",
        )
        parser.add_argument(
            "--group",
            required=True,
            help="Name of the staff group. Will be created if doesn't exist yet."
        )

    def handle(self, *args, **options):
        superuser = User.objects.filter(is_superuser=True).first()
        if options["responsible"]:
            responsible = User.objects.get(username=options["responsible"])
        else:
            responsible = superuser

        group, created = Group.objects.get_or_create(name=options["group"])

        with ZipFile(options["zipfile"]) as zf:
            import_from_zip(zf, superuser, responsible, group)


