from django.urls import path
from . import consumers

app_name = "task_ws"

websocket_urlpatterns = [
    path("interactive_python/", consumers.InteractivePythonConsumer.as_asgi(), name="interactive_python")
]
