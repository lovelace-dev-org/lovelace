from django import forms
from django.template import loader


class AdminFileWidget(forms.ClearableFileInput):
    template_name = "courses/widgets/modified_file_input.html"


class AdminTemplateBackendFileWidget(forms.ClearableFileInput):
    template_name = "courses/widgets/template_backend_input.html"


class ContentPreviewWidget(forms.Textarea):
    template_name = "courses/widgets/content_preview_widget.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget as an HTML string."""
        context = self.get_context(name, value, attrs)
        return self._render(self.template_name, context, renderer)


class WidgetRegistry:

    widgets = {}

    @classmethod
    def register_widget(cls, widget_cls):
        cls.widgets[widget_cls.handle] = widget_cls

    @classmethod
    def get_widget(cls, handle, instance, content):
        return cls.widgets[handle](instance, content)

    @classmethod
    def list_widgets(cls):
        return sorted(cls.widgets.keys())


class AnswerWidgetRegistry(WidgetRegistry):

    widgets = {}


class PreviewWidgetRegistry(WidgetRegistry):

    widgets = {}


class Widget:

    template = "courses/blank.html"
    handle = "blank"
    configurable = False

    def __init__(self, instance, content):
        self.instance = instance
        self.content = content

    def render(self, context):
        t = loader.get_template(self.template)
        return t.render(context)

    def get_configuration_form(self):
        return None


class AnswerWidget(Widget):

    pass


class PreviewWidget(Widget):

    pass

