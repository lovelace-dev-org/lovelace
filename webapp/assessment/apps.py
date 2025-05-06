from django.apps import AppConfig

class AssessmentConfig(AppConfig):

    name = "assessment"

    def ready(self):
        from assessment import markup, forms

        markup.register_markups()
        forms.register_edit_forms()
