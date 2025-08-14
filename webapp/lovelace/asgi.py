# mysite/asgi.py
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings.channels")

asgi_app = get_asgi_application()

from courses.middleware import WSTicketAuthMiddleware
from lovelace.routing import websocket_urlpatterns
from django.conf import settings

application = ProtocolTypeRouter(
    {
        "http": asgi_app,
        "websocket": OriginValidator(
            WSTicketAuthMiddleware(URLRouter(websocket_urlpatterns)),
            settings.ALLOWED_WS_ORIGINS,
        ),
    }
)
