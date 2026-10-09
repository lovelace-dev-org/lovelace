from courses.widgets import AnswerWidget, AnswerWidgetRegistry



class AnswerlessWidget(AnswerWidget):

    handle = "answerless"
    template = "answerless/widgets/answerless-widget.html"

def register_answer_widgets():
    AnswerWidgetRegistry.register_widget(AnswerlessWidget)
