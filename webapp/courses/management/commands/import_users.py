import json
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from utils.data import deserialize_python

class Command(BaseCommand):
    help = "Imports users from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "jsonfile",
            help="Path of the JSON file to be used as the import source"
        )
        parser.add_argument(
            "--group",
            required=False,
            help="Add users to the named group."
        )

    def handle(self, *args, **options):
        imported_users = []
        with open(options["jsonfile"], encoding="utf-8") as source:
            source_doc = json.load(source)
            for obj in deserialize_python(source_doc):
                if not User.objects.filter(username=obj.object.username).exists():
                    obj.save()
                    imported_users.append(obj.object)
                else:
                    print(
                        f"Can't import {obj.object.username}, username already taken.",
                        file=sys.stderr
                    )

        if options["group"]:
            group, created = Group.objects.get_or_create(name=options["group"])
            group.user_set.add(*imported_users)



