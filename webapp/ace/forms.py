from django import forms
from courses.widgets import PreviewWidgetRegistry
import ace.models

class AceWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = ace.models.AceWidgetSettings
        exclude = ["content", "instance"]


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
        self._preview_subform.save(commit)
        ace_settings = self._ace_subform.save(commit=False)
        ace_settings.instance = model_inst.instance
        ace_settings.content = model_inst.content
        model_inst.ace_settings = ace_settings
        if commit:
            ace_settings.save()
            model_inst.save()
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
