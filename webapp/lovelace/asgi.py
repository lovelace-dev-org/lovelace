# mysite/asgi.py
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.channels")

from lovelace.routing import websocket_urlpatterns
from django.conf import settings

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": OriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
            settings.ALLOWED_WS_ORIGINS,
        ),
    }
)
