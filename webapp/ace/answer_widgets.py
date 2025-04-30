from django.template import loader
from courses.widgets import AnswerWidget, AnswerWidgetRegistry
import ace.models
import ace.forms

class AceAnswerWidget(AnswerWidget):

    handle = "ace"
    template = "ace/widgets/ace-answer-widget.html"
    configurable = True

    def render(self, context):
        t = loader.get_template(self.template)
        settings = self.get_settings()
        context["ace_container_height"] = settings.editor_height
        context["ace_font_size"] = settings.font_size
        context["ace_mode"] = settings.language_mode
        context["ace_extra"] = settings.extra_settings or {}
        return t.render(context)

    def get_configuration_form(self):
        return ace.forms.AceWidgetConfigurationForm

    def get_settings(self):
        settings, created = ace.models.AceWidgetSettings.objects.get_or_create(
            instance=self.instance,
            content=self.content
        )
        return settings

def register_answer_widgets():
    AnswerWidgetRegistry.register_widget(AceAnswerWidget)
