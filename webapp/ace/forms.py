from django import forms
import ace.models

class AceWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = ace.models.AceWidgetSettings
        exclude = ["content", "instance"]

