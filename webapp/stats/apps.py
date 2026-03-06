from django.apps import AppConfig
from lovelace import register_plugin


class StatsConfig(AppConfig):
    name = "stats"
    verbose_name = "Lovelace stats"

    def ready(self):
        from stats import menu
        register_plugin(self.module, ["embed-menu"])
