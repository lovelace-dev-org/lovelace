from functools import wraps
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.translation import gettext as _


def management_api(function):

    @wraps(function)
    def wrap(request, *args, **kwargs):
        if settings.ENABLE_MANAGEMENT_API:
            if request.headers.get("x-lovelace-api-key") == settings.MANAGEMENT_API_KEY:
                return function(request, *args, **kwargs)

        return HttpResponseForbidden(_("API access denied"))

    return wrap
