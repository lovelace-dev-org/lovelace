import yaml
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import fields
from django.utils.translation import gettext as _
from courses.forms import ExerciseBackendForm
from multiexam.models import MultipleQuestionExamAttempt, ExamQuestionPool
from multiexam.utils import validate_exam, compare_exams, render_error
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
        self.fields["individual_exams"] = forms.BooleanField(
            required=False,
            label=_("Create invidivual exams for everyone"),
        )
        self.fields["key"] = forms.CharField(
            widget=forms.PasswordInput,
            label=_("Exam attempt key"),
            required=False,
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


class ExamAttemptRefreshForm(forms.Form):

    start = forms.DateTimeField(
        label=_("Refresh attempts from"),
        required=True,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    end = forms.DateTimeField(
        label=_("Refresh attempts until"),
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
    )




class ExamAttemptKeyForm(forms.Form):

    exam_key = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Exam attempt key"),
        required=True,
    )

    def clean_exam_key(self):
        key = self.cleaned_data["exam_key"]
        if not self._attempt.check_key(key):
            raise ValidationError(_("Invalid key"))

    def __init__(self, *args, **kwargs):
        self._attempt = kwargs.pop("attempt")
        super().__init__(*args, **kwargs)



class QuestionPoolForm(ExerciseBackendForm):

    def clean(self):
        cleaned_data = super().clean()
        content_per_lang = {}
        for lang_code, __ in settings.LANGUAGES:
            memoryfile = cleaned_data.get(f"fileinfo_{lang_code}")
            try:
                if memoryfile:
                    content = yaml.safe_load(memoryfile.file)
                    content_per_lang[lang_code] = content
                else:
                    try:
                        existing = ExamQuestionPool.objects.get(id=cleaned_data["id"].id)
                    except ExamQuestionPool.DoesNotExist:
                        continue
                    else:
                        existing_file = getattr(existing, f"fileinfo_{lang_code}")
                        if existing_file:
                            with existing_file.open() as f:
                                content = yaml.safe_load(f)
                                content_per_lang[lang_code] = content
                        continue

            except yaml.YAMLError as e:
                self.add_error(
                    f"fileinfo_{lang_code}",
                    f"Parsing error in YAML file: {e}"
                )
                return

            valid, errors = validate_exam(content)
            if not valid:
                for __, error in errors.items():
                    self.add_error(
                        f"fileinfo_{lang_code}",
                        render_error(error)
                    )
                return

        if len(content_per_lang.keys()) > 1:
            valid, errors = compare_exams(
                content_per_lang,
                primary_key=settings.MODELTRANSLATION_DEFAULT_LANGUAGE
            )
            if not valid:
                for lang_code, msg in errors:
                    self.add_error(f"fileinfo_{lang_code}", msg)
                return








