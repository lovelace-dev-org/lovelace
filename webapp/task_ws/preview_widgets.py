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
        return t.render(context)

    def get_configuration_form(self, data=None, prefix=None):
        return task_ws.forms.XtermWidgetConfigurationForm(
            data,
            instance=self.get_settings(),
            prefix=prefix
        )

    def get_settings(self):
        settings, created = task_ws.models.XtermWidgetSettings.objects.get_or_create(
            instance=self.instance,
            content=self.content
        )
        return settings

def register_preview_widgets():
    PreviewWidgetRegistry.register_widget(XtermPreviewWidget)
