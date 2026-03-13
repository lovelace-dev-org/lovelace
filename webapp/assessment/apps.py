from django.apps import AppConfig
from lovelace import register_plugin

class AssessmentConfig(AppConfig):

    name = "assessment"

    def ready(self):
        from assessment import markup, forms
        from assessment import includes

        register_plugin(self.module, [
            "base-static", "embed-menu", "embed-extra", "answer-actions",
            "export", "import", "task_reference", "freeze", "clone",
        ])
        markup.register_markups()
        forms.register_edit_forms()
