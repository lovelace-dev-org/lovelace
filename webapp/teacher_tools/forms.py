from django import forms
from django.conf import settings
from django.utils.translation import gettext as _
from teacher_tools.models import MossSettings, ReminderTemplate

class MossnetForm(forms.ModelForm):
    
    class Meta:
        model = MossSettings
        fields = ["language", "file_extensions", "exclude_filenames", "exclude_subfolders", "matches"]

    matches = forms.IntegerField(label=_("Number of matches to show"))
    base_files = forms.FileField(
        widget=forms.FileInput(attrs={"multiple": "multiple"}),
        label=_("Upload base files"),
        required=False,
    )
    versions = forms.ChoiceField(
        widget=forms.RadioSelect,
        label=_("Choose which version(s) of the answers are analysed"),
        choices=(
            ("newest", _("Latest version only (recommended)")),
            ("all", _("Include all versions (NOTE: they will match amongst themselves)"))
        ),
    )
    save_settings = forms.BooleanField(
        label=_("Save settings for this exercise"),
        required=False
    )

    def __init__(self, *args, **kwargs):
        other_instances = kwargs.pop("other_instances")
        super().__init__(*args, **kwargs)

        self.fields["include_instances"] = forms.MultipleChoiceField(
            choices=((instance.slug, instance.name) for instance in other_instances),
            label=_("Include answers from other instances"),
            required=False
        )


class ReminderForm(forms.ModelForm):

    class Meta:
        model = ReminderTemplate
        fields = ["title", "header", "footer"]
        widgets = {
            "header": forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            "footer": forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
        }

    reminder_action = forms.ChoiceField(
        widget=forms.HiddenInput,
        choices=(("generate", "generate"), ("send", "send")),
        initial="generate"
    )
    save_template = forms.BooleanField(
        label=_("Save template for this instance"),
        required=False
    )
