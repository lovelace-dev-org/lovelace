from django.apps import AppConfig
from lovelace import register_plugin

class AssessmentConfig(AppConfig):

    name = "assessment"

    def ready(self):
        from assessment import markup, forms
        from assessment import menu

        register_plugin(self.module, ["embed-menu"])
        markup.register_markups()
        forms.register_edit_forms()

