import os
import pwd
from django.core.management.base import BaseCommand

template = \
"""
import dotenv
import os
import sys
from django.core.wsgi import get_wsgi_application
mask = 0o77

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings.production")

if os.stat("{env_path}").st_mode & mask:
    sys.exit("Insecure .env permissions, refusing to start")

dotenv.load_dotenv("{env_path}")
application = get_wsgi_application()
"""


class Command(BaseCommand):
    help = "Create a wsgi script that can be executed by apache. Needs to be run as root."

    def add_arguments(self, parser):
        parser.add_argument(
            "script_path",
            help="Path for the sript file, should be under apache root (e.g. /var/www)"
        )
        parser.add_argument(
            "--env_path",
            required=True,
            help="Path to the .env file to use for settings",
        )
        parser.add_argument(
            "--owner",
            help="Owner of the sript file (default: apache)",
            default="apache"
        )


    def handle(self, *args, **options):
        contents = template.format(env_path=options["env_path"])
        with open(options["script_path"], "w", encoding="utf-8") as target:
            target.write(contents)

        pwrec = pwd.getpwnam(options["owner"])
        uid = pwrec.pw_uid
        gid = pwrec.pw_gid
        os.chown(options["script_path"], uid, gid)
        os.chmod(options["script_path"], 0o700)







