from django.urls import reverse
from django.utils.text import slugify
import courses.models as cm
import logging

logger = logging.getLogger(__name__)

class BrokenLinkWarning(Exception):
    pass


def parse_link_url(address, context=None):
    try:
        server_side, client_side = address.split("#", 1)
    except ValueError:
        server_side = address
        client_side = None

    if server_side.strip() == "":
        final_address = "#" + (client_side or "")
        target = "_self"
    else:
        target = "_blank"

        if server_side.startswith("file:"):
            file_slug = server_side.split("file:", 1)[1]
            try:
                mediafile = cm.File.objects.get(name=file_slug)
            except cm.File.DoesNotExist as e:
                raise BrokenLinkWarning from e
            else:
                if context.get("course"):
                    final_address = reverse(
                        "courses:download_embedded_file",
                        kwargs={
                            "course": context["course"],
                            "instance": context["instance"],
                            "mediafile": mediafile,
                        },
                    )
                else:
                    final_address = ""
        else:
            slugified = slugify(server_side, allow_unicode=True)
            if server_side == slugified and context is not None:
                # internal address
                try:
                    content = cm.ContentPage.objects.get(slug=slugified)
                except cm.ContentPage.DoesNotExist as e:
                    logger.warning(f"Found broken link reference: {slugified}")
                    raise BrokenLinkWarning(slugified) from e
                else:
                    if context.get("course"):
                        final_address = reverse(
                            "courses:content",
                            args=[context["course"], context["instance"], content],
                        )
                        if client_side is not None:
                            final_address = final_address.rstrip("/") + "#" + client_side
                    else:
                        final_address = ""
            else:
                # external address
                final_address = address

    return final_address, target
