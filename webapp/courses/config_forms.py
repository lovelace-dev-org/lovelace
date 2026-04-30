from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django import forms

from utils.management import TranslationStaffForm

import courses.models as cm

class MultipleChoiceExerciseChoiceForm(TranslationStaffForm):

    class Meta:
        model = cm.MultipleChoiceExerciseAnswer
        fields = ["correct", "answer", "hint", "comment"]


class CheckboxExerciseChoiceForm(TranslationStaffForm):

    class Meta:
        model = cm.CheckboxExerciseAnswer
        fields = ["correct", "weight", "answer", "hint", "comment"]


class TextfieldExerciseAnswerForm(TranslationStaffForm):

    class Meta:
        model = cm.TextfieldExerciseAnswer
        fields = ["correct", "regexp", "answer", "hint", "comment"]
