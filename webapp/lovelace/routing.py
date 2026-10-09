from django.urls import path, include
from channels.routing import URLRouter
from lovelace import plugins as lovelace_plugins

websocket_urlpatterns = []

for app in lovelace_plugins["routing"]:
    websocket_urlpatterns.append(
        path(f"{app.__name__}/", URLRouter(app.routing.websocket_urlpatterns))
    )
