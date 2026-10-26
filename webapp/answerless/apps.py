from django.apps import AppConfig
from lovelace import register_plugin


class AnswerlessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'answerless'

    def ready(self):
        from answerless import answer_widgets
        answer_widgets.register_answer_widgets()
        register_plugin(self.module, ["export", "import", "urls"])


