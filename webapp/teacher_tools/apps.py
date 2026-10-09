from django.apps import AppConfig
from lovelace import register_plugin


class TeacherToolsConfig(AppConfig):
    name = "teacher_tools"
    verbose_name = "Lovelace teacher's tools"

    def ready(self):
        from teacher_tools import includes
        register_plugin(self.module, ["user-menu", "embed-menu"])
