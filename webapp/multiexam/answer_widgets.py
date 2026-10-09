from courses.widgets import AnswerWidget, AnswerWidgetRegistry



class MultiExamAnswerWidget(AnswerWidget):

    handle = "multiexam"
    template = "multiexam/widgets/multiexam-answer-widget.html"

def register_answer_widgets():
    AnswerWidgetRegistry.register_widget(MultiExamAnswerWidget)
