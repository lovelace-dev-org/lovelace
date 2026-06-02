from decimal import Decimal
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


class OriginFilterSelect(forms.Select):
    template_name = "courses/widgets/origin-filter-select.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["options_url"] = self.attrs["options_url"]
        context["widget"]["origins"] = self.attrs["origin_options"]
        return context


class NoTrailingZerosInput(forms.NumberInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format_value(self, value):
        if value is not None and isinstance(value, Decimal):
            while (abs(value.as_tuple().exponent) > 1 and value.as_tuple().digits[-1] == 0):
                value = Decimal(str(value)[:-1])
            return value

class WidgetRegistry:

    widgets = {}

    @classmethod
    def register_widget(cls, widget_cls):
        cls.widgets[widget_cls.handle] = widget_cls

    @classmethod
    def get_widget(cls, handle, course, slug):
        return cls.widgets[handle](course, slug)

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

    def __init__(self, course, slug):
        self.slug = slug
        self.course = course

    def render(self, context):
        t = loader.get_template(self.template)
        return t.render(context)

    def get_configuration_form(self, request, data=None, prefix=None):
        return None

    def export(self, instance, export_target):
        pass


class AnswerWidget(Widget):

    pass


class PreviewWidget(Widget):

    pass


