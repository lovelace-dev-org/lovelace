from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django import forms

from utils.management import TranslationStaffForm

import courses.models as cm

MultipleChoiceConfigForm = forms.inlineformset_factory(
    cm.ContentPage,
    cm.MultipleChoiceExerciseAnswer,
    fields=["correct", "answer", "hint", "comment"],
    extra=1,
)

cm.ContentPage.register_config_form("MULTIPLE_CHOICE_EXERCISE", MultipleChoiceConfigForm)
