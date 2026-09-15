from django import forms
from django.forms import fields
from django.forms.models import ModelMultipleChoiceField
from django.urls import reverse
from django.utils.translation import gettext as _


from courses.fields import ModelOriginFilterMultiField
from courses.widgets import OriginFilterMultiSelect
import courses.models as cm
from utils.management import TranslationStaffForm

from .models import ExamTaskSettings, ExamTaskAttempt


class ExamTaskSettingsForm(forms.ModelForm):

    class Meta:
        model = ExamTaskSettings
        fields = ["task_pool", "avoid_same"]

    @property
    def _options_url(self):
        return reverse("courses:get_accessible_pages")

    def __init__(self, *args, **kwargs):
        course_inst = kwargs.pop("course_inst")
        super().__init__(*args, **kwargs)

        self.fields["task_pool"] = ModelMultipleChoiceField(
            widget=forms.SelectMultiple(attrs={
                "size": 10,
            }),
            queryset=(
                cm.EmbeddedLink.objects.filter(instance=course_inst)
                .select_related("parent", "embedded_page")
                .defer("parent__content", "embedded_page__content")
                .order_by("parent__name", "embedded_page__name")
            )
        )


class ExamTaskAttemptForm(forms.ModelForm):

    class Meta:
        model = ExamTaskAttempt
        fields = ["title", "start", "end", "user"]

    def clean(self):
        cleaned_data = super().clean()
        if other_attempts := ExamTaskAttempt.objects.filter(
            user=cleaned_data["user"],
            instance=self._course_inst,
            task=self._exam_task,
            parent=self._parent,
        ).exclude(id=self._instance.id):
            if other_attempts.filter(
                end__gte=cleaned_data["start"],
                start__lte=cleaned_data["end"],
            ).exists():
                self.add_error("start", _("Time interval overlaps with another atttempt"))
                self.add_error("end", _("Time interval overlaps with another atttempt"))

    def __init__(self, *args, **kwargs):
        self._course_inst = kwargs.pop("course_inst")
        self._exam_task = kwargs.pop("exam_task")
        self._parent = kwargs.pop("parent")
        self._instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        if not kwargs.get("instance"):
            self.fields["start"] = forms.DateTimeField(
                label=_("Starting date and time"),
                required=True,
                input_formats=["%Y-%m-%dT%H:%M"],
                widget=forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
            )
            self.fields["end"] = forms.DateTimeField(
                label=_("Ending date and time"),
                required=True,
                input_formats=["%Y-%m-%dT%H:%M"],
                widget=forms.widgets.DateTimeInput(attrs={"type": "datetime-local"}),
            )
        self.fields["user"] = forms.ModelChoiceField(
            queryset=self._course_inst.enrolled_users.get_queryset(),
            required=False,
        )

        self.fields["propagate"] = forms.BooleanField(
            label=_("Apply to all exam tasks on this page"),
            required=False
        )
