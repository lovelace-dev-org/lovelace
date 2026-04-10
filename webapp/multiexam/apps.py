from django.apps import AppConfig
from lovelace import register_plugin


class MultiExamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "multiexam"

    def ready(self):
        from multiexam import answer_widgets
        answer_widgets.register_answer_widgets()
        register_plugin(self.module, ["export", "import"])
