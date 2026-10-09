from courses.widgets import AnswerWidget, AnswerWidgetRegistry


class RoutineAnswerWidget(AnswerWidget):

    handle = "routine"
    template = "routine_exercise/widgets/routine-answer-widget.html"

def register_answer_widgets():
    AnswerWidgetRegistry.register_widget(RoutineAnswerWidget)
