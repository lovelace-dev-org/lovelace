from django.template import loader
import courses.models as cm
import courses.forms
from courses.widgets import AnswerWidget, AnswerWidgetRegistry

class CheckboxAnswerWidget(AnswerWidget):

    handle = "checkbox"
    template = "courses/widgets/checkbox-answer-widget.html"


class RadioAnswerWidget(AnswerWidget):

    handle = "radio"
    template = "courses/widgets/radio-answer-widget.html"


class TextfieldAnswerWidget(AnswerWidget):

    handle = "textfield"
    template = "courses/widgets/textfield-answer-widget.html"
    configurable = True

    def render(self, context):
        t = loader.get_template(self.template)
        settings = self.get_settings()
        context["widget_rows"] = settings.rows
        return t.render(context)

    def get_configuration_form(self):
        return courses.forms.TextfieldWidgetConfigurationForm

    def get_settings(self):
        settings, created = cm.TextfieldWidgetSettings.objects.get_or_create(
            instance=self.instance,
            content=self.content
        )
        return settings


class FileAnswerWidget(AnswerWidget):

    handle = "file"
    template = "courses/widgets/file-answer-widget.html"

def register_answer_widgets():
    AnswerWidgetRegistry.register_widget(AnswerWidget)
    AnswerWidgetRegistry.register_widget(CheckboxAnswerWidget)
    AnswerWidgetRegistry.register_widget(RadioAnswerWidget)
    AnswerWidgetRegistry.register_widget(TextfieldAnswerWidget)
    AnswerWidgetRegistry.register_widget(FileAnswerWidget)
