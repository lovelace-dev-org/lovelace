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
            min_value = 1,
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
        widgets = {
            "open_from": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
            "open_to": forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    refresh = forms.BooleanField(required=False, label=_("Refresh exam to latest version"))
