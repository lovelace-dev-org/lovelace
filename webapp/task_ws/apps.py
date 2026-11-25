import sys
import re
import httpx
from django.conf import settings
from django.apps import AppConfig
from lovelace import register_plugin


def validate_ce_host():
    def is_compiler_explorer_release_str(s: str) -> bool:
        return bool(re.fullmatch(r"gh\-\d+", s))

    if settings.COMPILER_EXPLORER_URL:
        from urllib.parse import urlparse
        parsed = urlparse(settings.COMPILER_EXPLORER_URL)
        if parsed.scheme not in ("http", "https"):
            print(
                "\033[93mCOMPILER_EXPLORER_URL must start with http:// or https://\033[0m", file=sys.stderr)

        with httpx.Client() as client:
            try:
                response = client.get(
                    f"{settings.COMPILER_EXPLORER_URL}/api/releaseBuild",
                    headers={
                        "Accept": "text/html",
                    },
                )
                if response.status_code != 200:
                    print(
                        f"\033[93mCOMPILER_EXPLORER_URL is not responding correctly, got status code {response.status_code}\033[0m", file=sys.stderr
                    )
                if is_compiler_explorer_release_str(response.text):
                    return  # probably valid CE host
            except httpx.RequestError as exc:
                pass  # probably invalid CE host
            print(
                f"\033[93mWARNING: COMPILER_EXPLORER_URL does not seem to point to a valid Compiler Explorer instance or it is inaccessible\033[0m", file=sys.stderr)
    else:
        print("\033[93mCOMPILER_EXPLORER_URL is not set\033[0m",
              file=sys.stderr)


class TaskWsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "task_ws"

    def ready(self):
        from . import routing, preview_widgets
        register_plugin(self.module, ["export", "import", "routing"])
        preview_widgets.register_preview_widgets()

        # todo is this a valid check to check if we're running as a ws server?
        if "task_ws" in settings.INSTALLED_APPS and "daphne" in settings.INSTALLED_APPS:
            validate_ce_host()
