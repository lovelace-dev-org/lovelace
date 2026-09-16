from django import forms
import task_ws.models

class XtermWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = task_ws.models.XtermWidgetSettings
        exclude = ["name", "slug", "course"]


class TurtleWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = task_ws.models.TurtleWidgetSettings
        exclude = ["name", "slug", "course"]

class SQLWidgetConfigurationForm(forms.ModelForm):

    class Meta:
        model = task_ws.models.SQLWidgetSettings
        exclude = ["name", "slug", "course"]
