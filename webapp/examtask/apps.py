from django.apps import AppConfig
from lovelace import register_plugin


class ExamtaskConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'examtask'

    def ready(self):
        register_plugin(self.module, ["content-follow", "export", "import", "urls"])
