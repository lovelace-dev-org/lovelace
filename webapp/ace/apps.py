from django.apps import AppConfig
from lovelace import register_plugin

class AceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ace"

    def ready(self):
        from ace import includes, markup, forms, answer_widgets
        answer_widgets.register_answer_widgets()
        register_plugin(self.module, ["base-static", "export", "import", "context_links", "urls"])
        markup.register_markups()
        forms.register_edit_forms()

