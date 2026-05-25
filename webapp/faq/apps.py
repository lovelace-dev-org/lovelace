from django.apps import AppConfig
from lovelace import register_plugin

class FaqConfig(AppConfig):

    name = "faq"

    def ready(self):
        from faq import includes
        register_plugin(self.module, [
            "export", "import", "freeze", "clone", "task_reference",
            "base-static", "embed-extra", "exercise-triggers",
        ])

