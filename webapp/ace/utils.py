import glob
import os
from django.apps import apps

def get_available_modes():
    app_path = apps.get_app_config("ace").path
    ace_static_path = os.path.join(app_path, "static", "ace", "ace")
    return [
        name.removeprefix("mode-").removesuffix(".js")
        for name in glob.glob("mode-*.js", root_dir=ace_static_path)
    ]



