from django.apps import AppConfig
from lovelace import register_plugin


class TicketingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ticketing'

    def ready(self):
        from ticketing import includes
        register_plugin(self.module, ["urls", "user-menu"])

