from django import forms
from django.utils.translation import gettext_lazy as _
from utils.management import add_translated_charfields


class SystemMessageForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_translated_charfields(
            self, "content",
            _("Message content ({lang} - default)"),
            _("Message content ({lang})"),
            require_default=True
        )
        self.fields["expires"] = forms.DateTimeField(
            label=_("Time this message expires"),
            required=True,
            input_formats=["%Y-%m-%dT%H:%M"],
            widget=forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
        )


class DataRetentionForm(forms.Form):

    execute = forms.BooleanField(required=False, initial=False)
