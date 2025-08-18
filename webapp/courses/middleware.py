import json
import urllib
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.utils.translation import gettext as _
from django.conf import settings
import redis.asyncio as redis

if "shibboleth" in settings.INSTALLED_APPS:
    from shibboleth.middleware import (
        ShibbolethRemoteUserMiddleware,
        ShibbolethValidationError,
    )
    from courses.models import UserProfile

    class LovelaceShibbolethRemoteUser(ShibbolethRemoteUserMiddleware):
        def make_profile(self, user, shib_meta):
            profile = UserProfile()
            profile.user = user
            try:
                profile.student_id = int(shib_meta.get("student_id", "").rsplit(":", 1)[-1])
                profile.first_name = str(shib_meta.get("first_name").encode("latin-1"), "utf-8")
                profile.last_name = str(shib_meta.get("last_name").encode("latin-1"), "utf-8")
            except ValueError:
                pass
            else:
                profile.save()

    class ShibbolethExceptionReporter:
        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            response = self.get_response(request)
            return response

        def process_exception(self, request, exception):
            if isinstance(exception, ShibbolethValidationError):
                return HttpResponseBadRequest(
                    _(
                        "Remote authentication did not provide an email address. "
                        "The most likely cause is a delay between systems. "
                        "Please wait a few hours and try again."
                    )
                )
            return None


class WSTicketAuthMiddleware:

    def __init__(self, app):
        self.app = app
        self.pool = redis.ConnectionPool.from_url(settings.TICKET_CACHE_URL)
        self.client = redis.Redis(connection_pool=self.pool)

    async def __call__(self, scope, receive, send):
        query = urllib.parse.parse_qs(scope["query_string"].decode("utf-8"))
        try:
            ticket = query["ticket"][0]
        except KeyError:
            scope["user"] = None
        else:
            ticket_data = await self.client.get(ticket)
            if not ticket_data:
                scope["user"] = None
            else:
                ticket_data = json.loads(ticket_data)
                scope["user"] = ticket_data["user_id"]

        return await self.app(scope, receive, send)
