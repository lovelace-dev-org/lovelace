from django.apps import AppConfig

class CoursesConfig(AppConfig):

    name = "courses"

    def ready(self):
        from courses import blocktags, markup, edit_forms
        blocktags.register_tags()
        markup.register_markups()
        edit_forms.register_edit_forms()
