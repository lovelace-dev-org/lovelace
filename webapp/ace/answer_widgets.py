from django.template import loader
from django.urls import reverse
from courses.widgets import AnswerWidget, AnswerWidgetRegistry, PreviewWidgetRegistry
from utils.files import get_file_contents
import ace.models
import ace.forms

class AceAnswerWidget(AnswerWidget):

    handle = "ace"
    template = "ace/widgets/ace-answer-widget.html"
    configurable = True

    def _add_context(self, settings, context):
        context["ace_container_height"] = settings.editor_height
        context["ace_font_size"] = settings.font_size
        context["ace_mode"] = settings.language_mode
        context["ace_extra"] = settings.extra_settings or {}
        context["ace_layout"] = "vertical"
        context["widget_slug"] = settings.key_slug
        if settings.base_file:
            context["ace_initial_content"] = get_file_contents(settings.base_file).decode("utf-8")

    def render(self, context):
        t = loader.get_template(self.template)
        settings = self.get_settings()
        self._add_context(settings, context)
        return t.render(context)

    def get_configuration_form(self, request, data=None, prefix=None):
        return ace.forms.AceWidgetConfigurationForm(
            data, instance=self.get_settings(), prefix=prefix, request=request
        )

    def get_settings(self):
        try:
            settings = ace.models.AceWidgetSettings.objects.get(
                instance=self.instance,
                key_slug=self.key
            )
        except ace.models.AceWidgetSettings.DoesNotExist:
            settings = ace.models.AceWidgetSettings(
                instance=self.instance,
                key_slug=self.key
            )
        return settings


class AcePlusAnswerWidget(AnswerWidget):

    handle = "ace-plus"
    template = "ace/widgets/ace-answer-widget.html"
    configurable = True

    def __init__(self, instance, content):
        super().__init__(instance, content)
        self.settings = self.get_settings()
        self.ace_widget = AnswerWidgetRegistry.get_widget(
            "ace", self.instance, self.key
        )
        if self.settings.preview_widget:
            self.preview_widget = PreviewWidgetRegistry.get_widget(
                self.settings.preview_widget, self.instance, self.key
            )
        else:
            self.preview_widget = None

    def render(self, context):
        ace_settings = self.ace_widget.get_settings()
        self.ace_widget._add_context(ace_settings, context)
        if self.preview_widget:
            context["ace_preview_widget"] = self.preview_widget.render(context)
            context["ace_preview_cb"] = self.preview_widget.receive_callback
            context["ace_preview_ws"] = self.settings.ws_address
        context["ace_layout"] = self.settings.layout
        t = loader.get_template(self.template)
        return t.render(context)

    def get_configuration_form(self, request, data=None, prefix=None):
        ace_form = self.ace_widget.get_configuration_form(request, data, prefix="ace")
        if self.preview_widget:
            preview_form = self.preview_widget.get_configuration_form(request, data, prefix="extra")
        elif data:
            preview_widget = PreviewWidgetRegistry.get_widget(
                data["preview_widget"], self.instance, self.key
            )
            preview_form = preview_widget.get_configuration_form(request, data, prefix="extra")
        else:
            preview_form = None

        return ace.forms.AcePlusWidgetConfigurationForm(
            data, instance=self.settings,
            widget_change_url=reverse("ace:preview_subform", kwargs={
                "instance": self.instance,
                "key": self.key,
            }),
            prefix=prefix,
            ace_form=ace_form,
            preview_form=preview_form,
        )

    def get_settings(self):
        try:
            settings = ace.models.AcePlusWidgetSettings.objects.get(
                instance=self.instance,
                key_slug=self.key
            )
        except ace.models.AcePlusWidgetSettings.DoesNotExist:
            settings = ace.models.AcePlusWidgetSettings(
                instance=self.instance,
                key_slug=self.key
            )
        return settings


def register_answer_widgets():
    AnswerWidgetRegistry.register_widget(AceAnswerWidget)
    AnswerWidgetRegistry.register_widget(AcePlusAnswerWidget)
