from django.template import loader
from courses.widgets import PreviewWidget, PreviewWidgetRegistry
import task_ws.models
import task_ws.forms


class XtermPreviewWidget(PreviewWidget):

    handle = "xterm"
    template = "task_ws/widgets/xterm-preview-widget.html"
    configurable = True
    receive_callback = "xtermwidget.receive"

    def render(self, context):
        t = loader.get_template(self.template)
        settings = self.get_settings()
        context["xterm_rows"] = settings.rows
        context["widget_slug"] = settings.key_slug
        return t.render(context)

    def get_configuration_form(self, request, data=None, prefix=None):
        return task_ws.forms.XtermWidgetConfigurationForm(
            data,
            instance=self.get_settings(),
            prefix=prefix
        )

    def get_settings(self):
        try:
            settings = task_ws.models.XtermWidgetSettings.objects.get(
                instance=self.instance,
                key_slug=self.key
            )
        except task_ws.models.XtermWidgetSettings.DoesNotExist:
            settings = task_ws.models.XtermWidgetSettings(
                instance=self.instance,
                key_slug=self.key
            )
        return settings


class TurtlePreviewWidget(PreviewWidget):

    handle = "turtle"
    template = "task_ws/widgets/turtle-preview-widget.html"
    configurable = True
    receive_callback = "turtlewidget.receive"

    def render(self, context):
        t = loader.get_template(self.template)
        settings = self.get_settings()
        context["widget_slug"] = settings.key_slug
        return t.render(context)

    def get_configuration_form(self, request, data=None, prefix=None):
        return task_ws.forms.TurtleWidgetConfigurationForm(
            data,
            instance=self.get_settings(),
            prefix=prefix
        )

    def get_settings(self):
        try:
            settings = task_ws.models.TurtleWidgetSettings.objects.get(
                instance=self.instance,
                key_slug=self.key
            )
        except task_ws.models.TurtleWidgetSettings.DoesNotExist:
            settings = task_ws.models.TurtleWidgetSettings(
                instance=self.instance,
                key_slug=self.key
            )
        return settings


def register_preview_widgets():
    PreviewWidgetRegistry.register_widget(XtermPreviewWidget)
    PreviewWidgetRegistry.register_widget(TurtlePreviewWidget)
