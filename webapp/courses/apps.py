from django.apps import AppConfig

class CoursesConfig(AppConfig):

    name = "courses"

    def ready(self):
        from courses import blocktags, markup, edit_forms, answer_widgets
        blocktags.register_tags()
        markup.register_markups()
        edit_forms.register_edit_forms()
        answer_widgets.register_answer_widgets()
