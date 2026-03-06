from django.apps import AppConfig
from lovelace import register_plugin


class FeedbackConfig(AppConfig):
    name = "feedback"
    verbose_name = "Lovelace feedback"

    def ready(self):
        from feedback import menu
        register_plugin(self.module, ["embed-menu"])
