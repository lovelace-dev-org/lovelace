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

        # self.fields["task_pool"] = ModelOriginFilterMultiField(
        #     widget=OriginFilterMultiSelect(attrs={
        #         "options_url": self._options_url,
        #         "origin_options": accessible_courses,
        #         "initial_origin": course,
        #         "size": 10,
        #     }),
        #     label=_("Select tasks"),
        #     queryset=accessible_pages,
        #     required=True,
        #     model=cm.ContentPage,
        #     access_list=accessible_courses,
        # )


class ExamTaskAttemptForm(forms.ModelForm):

    class Meta:
        model = ExamTaskAttempt
        fields = ["title", "start", "end", "user"]

    def __init__(self, *args, **kwargs):
        enrolled_students = kwargs.pop("enrolled_students")
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
            queryset=enrolled_students,
            required=False,
        )

        self.fields["propagate"] = forms.BooleanField(
            label=_("Apply to all exam tasks on this page"),
            required=False
        )
