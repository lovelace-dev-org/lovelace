from django import forms
from django.utils.translation import gettext as _
import courses.models as cm
from teacher_tools.models import MossSettings, ReminderTemplate


class MossnetForm(forms.ModelForm):
    class Meta:
        model = MossSettings
        fields = [
            "language",
            "file_extensions",
            "exclude_filenames",
            "exclude_subfolders",
            "matches",
        ]


    def __init__(self, *args, **kwargs):
        other_instances = kwargs.pop("other_instances")
        super().__init__(*args, **kwargs)
        self.fields["matches"] = forms.IntegerField(label=_("Number of matches to show"))
        self.fields["base_files"] = forms.FileField(
            widget=forms.FileInput(attrs={"multiple": "multiple"}),
            label=_("Upload base files"),
            required=False,
        )
        self.fields["versions"] = forms.ChoiceField(
            widget=forms.RadioSelect,
            label=_("Choose which version(s) of the answers are analysed"),
            choices=(
                ("newest", _("Latest version only (recommended)")),
                ("all", _("Include all versions (NOTE: they will match amongst themselves)")),
            ),
        )
        self.fields["save_settings"] = forms.BooleanField(
            label=_("Save settings for this exercise"), required=False
        )

        self.fields["include_instances"] = forms.MultipleChoiceField(
            choices=((instance.slug, instance.name) for instance in other_instances),
            label=_("Include answers from other instances"),
            required=False,
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
        initial="generate",
    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["save_template"] = forms.BooleanField(
            label=_("Save template for this instance"), required=False
        )


class BatchGradingForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mode"] = forms.ChoiceField(
            widget=forms.RadioSelect,
            label=_("Grading mode"),
            required=True,
            choices=(
                ("latest", _("Only grade latest answer")),
                ("all", _("Grade all answers")),
            ),
            initial="latest",
        )


class TransferRecordsForm(forms.Form):
    # mode = forms.ChoiceField(
    # widget=forms.RadioSelect,
    # label=_("Transfer action"),
    # required=True,
    # choices=(
    # ("move", _("Move records")),
    # ("copy", _("Copy records")),
    # ),
    # initial="copy"
    # )
    def __init__(self, *args, **kwargs):
        other_instances = kwargs.pop("instances")
        super().__init__(*args, **kwargs)

        self.fields["recalculate"] = forms.BooleanField(
            label=_("Recalculate points"),
            required=False,
        )

        self.fields["target_instance"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose target instance"),
            choices=[(c.id, c.name) for c in other_instances],
        )


class DeadlineExemptionForm(forms.ModelForm):

    class Meta:
        model = cm.DeadlineExemption
        fields = ["user", "contentgraph", "new_deadline"]
        widgets = {
            "new_deadline": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        students = kwargs.pop("students")
        available_content = kwargs.pop("graphs")
        super().__init__(*args, **kwargs)
        self.fields["contentgraph"].queryset = available_content
        self.fields["user"].queryset = students





