from django.apps import AppConfig
from lovelace import register_plugin

class TaskWsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "task_ws"

    def ready(self):
        from . import routing, preview_widgets
        register_plugin(self.module, ["routing"])
        preview_widgets.register_preview_widgets()
