from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django import forms
from django.utils.translation import gettext_lazy as _

from utils.management import TranslationStaffForm

import courses.models as cm
from courses.forms import TextfieldAnswerForm
from courses.widgets import AnswerWidgetRegistry

class MultipleChoiceExerciseChoiceForm(TranslationStaffForm):

    class Meta:
        model = cm.MultipleChoiceExerciseAnswer
        fields = ["correct", "answer", "hint", "comment"]
        trigger_cache = True



class CheckboxExerciseChoiceForm(TranslationStaffForm):

    class Meta:
        model = cm.CheckboxExerciseAnswer
        fields = ["correct", "weight", "answer", "hint", "comment"]
        trigger_cache = True


class TextfieldExerciseAnswerForm(TranslationStaffForm, TextfieldAnswerForm):

    class Meta:
        model = cm.TextfieldExerciseAnswer
        fields = ["correct", "regexp", "answer", "hint", "comment"]
        refresh_mode = "refresh"


class AnswerWidgetChangeForm(forms.ModelForm):

    class Meta:
        model = cm.ContentPage
        fields = ["answer_widget"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["answer_widget"] = forms.ChoiceField(
            widget = forms.Select(),
            choices = (
                [(None, _("--USE-DEFAULT--"))] +
                [(widget, widget) for widget in AnswerWidgetRegistry.list_widgets()]
            ),
            required=False
        )


