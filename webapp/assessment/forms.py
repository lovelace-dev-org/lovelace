from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import fields
from django.utils.translation import gettext as _
from assessment.models import AssessmentBullet, AssessmentSection
from utils.management import add_translated_charfields, TranslationStaffForm


class AddAssessmentForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        sheet = int(cleaned_data.get("sheet"))
        default_title = cleaned_data.get("title_" + settings.MODELTRANSLATION_DEFAULT_LANGUAGE)
        if not (sheet or default_title):
            raise ValidationError(
                _(f"Either title in default language, or existing sheet must be filled")
            )
        if cleaned_data["copy"] and not default_title:
            raise ValidationError(
                _(f"When making a copy, title is mandatory")
            )

    def __init__(self, *args, **kwargs):
        course_sheets = kwargs.pop("course_sheets")
        super().__init__(*args, **kwargs)

        add_translated_charfields(
            self,
            "title",
            _("Default sheet title ({lang}):"),
            _("Alternative sheet title ({lang}):"),
            require_default=False,
        )
        self.fields["sheet"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose sheet to use"),
            choices=[
                (0, _("----NEW--SHEET----")),
            ]
            + [(s.id, s.title) for s in course_sheets],
            required=False,
        )
        self.fields["copy"] = forms.BooleanField(
            label=_("Make a copy of selected sheet"),
            required=False
        )


class SectionForm(TranslationStaffForm):
    class Meta:
        model = AssessmentSection
        fields = ["title", "ordinal_number"]


class NewBulletForm(TranslationStaffForm):
    class Meta:
        model = AssessmentBullet
        fields = ["title", "tooltip", "point_value"]

    active_bullet = forms.IntegerField(widget=forms.HiddenInput, required=False)
    active_section = forms.CharField(widget=forms.HiddenInput, required=True)


_score_errors = {
    "required": _("required"),
    "max_value": _("> max"),
    "min_value": _("< 0"),
}


class AssessmentForm(forms.Form):

    def points_widget(self, bullet):
        return self[f"bullet-{bullet.id}-points"]

    def comment_widget(self, bullet):
        return self[f"bullet-{bullet.id}-comment"]

    def get_initial_for_field(self, field, field_name):
        default_value = super().get_initial_for_field(field, field_name)
        if self._assessment:
            try:
                _, id_str, ftype = field_name.split("-")
            except ValueError:
                if field_name == "correct":
                    return self._assessment.get("correct", False)
                if field_name == "complete":
                    return self._assessment.get("complete", False)
                return default_value

            try:
                if ftype == "points":
                    default_value = self._assessment["bullet_index"][id_str]["scored_points"]
                elif ftype == "comment":
                    default_value = self._assessment["bullet_index"][id_str]["comment"]
            except KeyError:
                default_value = None

        return default_value

    def __init__(self, *args, **kwargs):
        bullets_by_section = kwargs.pop("by_section")
        try:
            self._assessment = kwargs.pop("assessment")
        except KeyError:
            self._assessment = {}
        super().__init__(*args, **kwargs)

        for name, section in bullets_by_section.items():
            for bullet in section["bullets"]:
                self.fields[f"bullet-{bullet.id}-points"] = fields.FloatField(
                    max_value=bullet.point_value,
                    min_value=0,
                    label=bullet.title,
                    help_text=bullet.tooltip,
                    widget=forms.TextInput(attrs={"class": "points-input"}),
                    required=False,
                    error_messages=_score_errors,
                )
                self.fields[f"bullet-{bullet.id}-comment"] = fields.CharField(
                    widget=forms.TextInput(attrs={"class": "comment-input"}), required=False
                )

        self.fields["correct"] = forms.BooleanField(
            label=_("Mark this assessment as correct"), required=False
        )
        self.fields["complete"] = forms.BooleanField(
            label=_("This assessment is complete"), required=False
        )
        self.fields["suspect"] = forms.BooleanField(
            label=_("Mark the assessed submit as suspect"), required=False
        )
        self.fields["comment"] = forms.CharField(
            label=_("Add comment for other evaluators"),
            widget=forms.TextInput(attrs={"class": "comment-input"}), required=False
        )


class AssessmentBulletForm(TranslationStaffForm):
    class Meta:
        model = AssessmentBullet
        fields = ["title", "tooltip", "point_value"]
