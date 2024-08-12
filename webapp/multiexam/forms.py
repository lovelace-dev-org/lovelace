import yaml
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import fields
from django.utils.translation import gettext as _
from multiexam.models import MultipleQuestionExamAttempt
from utils.formatters import display_name
from utils.management import add_translated_charfields, TranslationStaffForm

class ExamAttemptForm(forms.ModelForm):

    class Meta:
        model = MultipleQuestionExamAttempt
        fields = ["open_from", "open_to"]
        widgets = {
            "open_from": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
            "open_to": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        students = kwargs.pop("students")
        available_questions = kwargs.pop("available_questions")
        super().__init__(*args, **kwargs)
        self.fields["question_count"] = forms.IntegerField(
            min_value=1,
            max_value=available_questions,
            label=_("Number of questions (max: {n})").format(n=available_questions),
        )
        self.fields["user_id"] = forms.ChoiceField(
            widget=forms.Select,
            required=False,
            choices=(
                [(None, _(" -- GENERAL EXAM --"))]
                + [(student.id, display_name(student)) for student in students]
            )
        )


class ExamAttemptDeleteForm(forms.Form):

    delete = forms.BooleanField(required=True, label=_("Confirm attempt deletion"))


class ExamAttemptSettingsForm(forms.ModelForm):

    class Meta:
        model = MultipleQuestionExamAttempt
        fields = ["open_from", "open_to"]

        # These cannot be currently used because the value attribute of datetime-local
        # uses a different syntax than what is gotten from the datetime field
        #widgets = {
        #    "open_from": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
        #    "open_to": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
        #}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["refresh"] = forms.BooleanField(
            required=False,
            label=_("Refresh exam to latest version")
        )


class QuestionPoolForm(forms.ModelForm):

    def _validate_yaml(self, memoryfile):
        """
        Validates that the yaml file is valid i.e. does not contain syntax errors
        """

        try:
            if memoryfile:
                content = yaml.safe_load(memoryfile.file)
        except yaml.YAMLError as e:
            raise ValidationError(f"Parsing error in YAML file: {e}") from e


    def clean(self):
        cleaned_data = super().clean()
        for lang_code, _ in settings.LANGUAGES:
            try:
                self._validate_yaml(cleaned_data[f"fileinfo_{lang_code}"])
            except ValidationError as e:
                self.add_error(f"fileinfo_{lang_code}", e)
