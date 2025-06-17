from django import forms
from django.urls import reverse
from courses import markupparser
from courses.widgets import AnswerWidgetRegistry, PreviewWidgetRegistry
import courses.models as cm
from courses.edit_forms import LineEditMixin, EmbeddedObjectEditForm
from utils.management import CourseMediaAdmin
import ace.models

class AceWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = ace.models.AceWidgetSettings
        exclude = ["instance", "key_slug"]

    def __init__(self, *args, **kwargs):
        self._accessible_files_qs = CourseMediaAdmin.media_access_list(kwargs.pop("request"), cm.File)
        super().__init__(*args, **kwargs)
        self.fields["base_file"].queryset = self._accessible_files_qs
        self.fields["base_file"].required = False


class AcePlusWidgetConfigurationForm(forms.ModelForm):

    has_inline = True

    class Meta:
        model = ace.models.AcePlusWidgetSettings
        fields = ["layout", "preview_widget", "ws_address"]

    def is_valid(self):
        if super().is_valid():
            if not self._preview_subform.is_valid():
                for field, error in self._preview_subform.errors.items():
                    self.errors[f"extra-{field}"] = error
                return False
            if not self._ace_subform.is_valid():
                for field, error in self._ace_subform.errors.items():
                    self.errors[f"ace-{field}"] = error
                return False
            return True
        return False

    def save(self, commit=True):
        model_inst = super().save(commit=False)
        preview_settings = self._preview_subform.save(commit=False)
        ace_settings = self._ace_subform.save(commit=False)
        ace_settings.instance = model_inst.instance
        ace_settings.key_slug = model_inst.key_slug
        preview_settings.key_slug = model_inst.key_slug
        model_inst.ace_settings = ace_settings
        if commit:
            ace_settings.save()
            model_inst.save()
            preview_settings.save()
        return model_inst

    def get_inline_formset(self):
        if self._preview_subform:
            return [self._preview_subform, self._ace_subform]
        return [self._ace_subform]

    def __init__(self, *args, **kwargs):
        widget_change_url = kwargs.pop("widget_change_url")
        self._ace_subform = kwargs.pop("ace_form")
        self._preview_subform = kwargs.pop("preview_form")
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        self.fields["preview_widget"] = forms.ChoiceField(
            widget = forms.Select(attrs={
                "onchange": "formtools.fetch_rows(event, this)",
                "data-change-url": widget_change_url,
            }),
            choices = (
                [(None, " -- ")] +
                [(widget, widget) for widget in PreviewWidgetRegistry.list_widgets()]
            ),
            required=True,
            initial=instance and instance.preview_widget,
        )


class AcePlusEditForm(LineEditMixin, EmbeddedObjectEditForm):

    _name = "ace-plus"
    _markup = ace.markup.AcePlusMarkup
    has_inline = True

    class Meta:
        model = ace.models.AcePlusWidgetSettings
        fields = ["key_slug", "layout", "preview_widget", "ws_address"]
        ref_field = "key_slug"
        markup = ace.markup.AcePlusMarkup

    def get_inline_formset(self):
        if self._preview_subform:
            return [self._preview_subform, self._ace_subform]
        return [self._ace_subform]

    def save(self, commit=True):
        model_inst = super().save(commit=False)
        model_inst.instance = self._context["instance"]
        preview_settings = self._preview_subform.save(commit=False)
        ace_settings = self._ace_subform.save(commit=False)
        ace_settings.instance = model_inst.instance
        ace_settings.key_slug = model_inst.key_slug
        preview_settings.key_slug = model_inst.key_slug
        model_inst.ace_settings = ace_settings
        if commit:
            ace_settings.save()
            model_inst.save()
            preview_settings.save()
        return model_inst

    def __init__(self, *args, **kwargs):
        super().__init__(*args, requires=False, **kwargs)
        instance = kwargs.get("instance")
        request = self._context["request"]
        course_inst = self._context["instance"]
        self.fields["preview_widget"] = forms.ChoiceField(
            widget = forms.Select(attrs={
                "onchange": "formtools.fetch_rows(event, this)",
                "data-change-url": reverse("ace:preview_subform", kwargs={
                    "instance": course_inst,
                    "key": "-default-",
                }),
            }),
            choices = (
                [(None, " -- ")] +
                [(widget, widget) for widget in PreviewWidgetRegistry.list_widgets()]
            ),
            required=True,
            initial=instance and instance.preview_widget,
        )
        self._ace_subform = AnswerWidgetRegistry.get_widget(
            "ace", course_inst, ""
        ).get_configuration_form(
            request,
            data=request.POST if self.is_bound else None,
            prefix="ace"
        )
        if instance and instance.preview_widget:
            preview_widget = PreviewWidgetRegistry.get_widget(
                instance.preview_widget, course_inst, instance.key_slug
            )
        elif request.POST:
            preview_widget = PreviewWidgetRegistry.get_widget(
                request.POST["preview_widget"], course_inst, request.POST["key_slug"]
            )
        else:
            preview_widget = None

        self._preview_subform = preview_widget and preview_widget.get_configuration_form(
            request,
            data=request.POST if self.is_bound else None,
            prefix="extra"
        )

def register_edit_forms():
    markupparser.MarkupParser.register_form("ace-plus", "edit", AcePlusEditForm)


