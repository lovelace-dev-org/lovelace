import os
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django import forms
from django.utils.translation import gettext_lazy as _

from utils.management import TranslationStaffForm
from routine_exercise.models import (
    RoutineExerciseBackendCommand,
    RoutineExerciseBackendFile,
    RoutineExerciseTemplate,
)
from routine_exercise.widgets import AdminRoutineBackendFileWidget

class BackendForm(forms.ModelForm):

    class Meta:
        model = RoutineExerciseBackendFile
        fields = ["filename", "fileinfo"]
        widgets = {
            "fileinfo": AdminRoutineBackendFileWidget
        }

    def get_initial_for_field(self, field, field_name):
        default_value = super().get_initial_for_field(field, field_name)
        if isinstance(field, forms.fields.FileField) and default_value:
            default_value.exercise_id = self._instance.exercise_id
            default_value.field_name = field_name
            default_value.filename = os.path.basename(default_value.name)

        return default_value

    def __init__(self, *args, **kwargs):
        self._instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)


class CommandForm(TranslationStaffForm):

    class Meta:
        model = RoutineExerciseBackendCommand
        fields = ["command"]


class TemplateForm(TranslationStaffForm):

    class Meta:
        model = RoutineExerciseTemplate
        fields = ["content"]
