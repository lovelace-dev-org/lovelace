from django.apps import AppConfig
from lovelace import register_plugin


class FeedbackConfig(AppConfig):
    name = "feedback"
    verbose_name = "Lovelace feedback"

    def ready(self):
        from feedback import includes
        register_plugin(
            self.module,
            ["export", "import", "base-static", "content-addon", "content-menu", "embed-menu"]
        )
