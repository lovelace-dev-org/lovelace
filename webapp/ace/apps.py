from django.apps import AppConfig
from lovelace import register_plugin

class AceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ace"

    def ready(self):
        from ace import answer_widgets
        answer_widgets.register_answer_widgets()
        register_plugin(self.module, ["urls"])


