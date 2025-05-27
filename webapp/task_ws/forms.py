from django import forms
import task_ws.models

class XtermWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = task_ws.models.XtermWidgetSettings
        exclude = ["content", "instance"]
