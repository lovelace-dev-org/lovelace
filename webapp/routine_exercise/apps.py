from django.apps import AppConfig
from lovelace import register_plugin

class RoutineExerciseConfig(AppConfig):

    name = "routine_exercise"

    def ready(self):
        from routine_exercise import answer_widgets
        answer_widgets.register_answer_widgets()
        register_plugin(self.module, ["export", "import", "content-follow"])


