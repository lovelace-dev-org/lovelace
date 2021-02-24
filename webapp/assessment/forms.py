from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import fields
from django.utils.translation import ugettext as _
from modeltranslation.forms import TranslationModelForm
from assessment.models import *

class AddAssessmentForm(forms.Form):

    def clean(self):
        cleaned_data = super().clean()
        sheet = int(cleaned_data.get("sheet"))
        default_title = cleaned_data.get("title_" + settings.MODELTRANSLATION_DEFAULT_LANGUAGE)
        if not (sheet or default_title):
            raise ValidationError(_(
                "Either title in default language ({lang})"
                " or existing sheet must be filled").format(
                    lang=settings.MODELTRANSLATION_DEFAULT_LANGUAGE
            ))
        if sheet and default_title:
            raise ValidationError(_(
                "Title fields cannot be filled when choosing an existing sheet"
            ))
    
    def __init__(self, *args, **kwargs):
        course_sheets = kwargs.pop("course_sheets")
        super().__init__(*args, **kwargs)
        
        for lang_code, lang_name in settings.LANGUAGES:
            self.fields["title_" + lang_code] = forms.CharField(
                label=_("Title for a new assessment sheet ({lang}):").format(lang=lang_code),
                required=False
            )
        
        self.fields["sheet"] = forms.ChoiceField(
            widget = forms.Select,
            label = _("Choose sheet to use"),
            choices = [(0, _("----NEW--SHEET----")), ] + [(s.id, s.title) for s in course_sheets],
            required=False
        )

class NewSectionForm(TranslationModelForm):

    class Meta:
        model = AssessmentBullet
        fields = ["section", "title", "tooltip", "point_value"]
        
        
class NewBulletForm(TranslationModelForm):

    class Meta:
        model = AssessmentBullet
        fields = ["title", "tooltip", "point_value"]
        
    active_bullet = forms.IntegerField(
        widget=forms.HiddenInput,
        required=False
    )
    active_section = forms.CharField(
        widget=forms.HiddenInput,
        required=True
    )
    

class AssessmentForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        bullets = kwargs.pop("bullets")
        super().__init__(*args, **kwargs)
        
        for bullet in bullets.order_by("section", "ordinal_number"):
            self.fields["bullet-{}-points".format(bullet.id)] = fields.DecimalField(
                max_digits=5,
                decimal_places=2,
                label=bullet.title,
            )
            self.fields["bullet-{}-comment".format(bullet.id)] = fields.TextField(
                widget=forms.TextInput,
            )

        
class AssessmentBulletForm(TranslationModelForm):
    class Meta:
        model = AssessmentBullet
        fields = ["title", "tooltip", "point_value"]
        
    
class RenameSectionForm(forms.Form):
    
    name = forms.CharField(
        required=True
    )
    active_section = forms.CharField(
        widget=forms.HiddenInput,
        required=True
    )

    def clean_name(self):
        name = self.cleaned_data["name"]
        if name in self.sections:
            raise ValidationError(_("Section name is already used in this assessment sheet."))
    
    def __init__(self, *args, **kwargs):
        if "sections" in kwargs:
            self.sections = kwargs.pop("sections")
        super().__init__(*args, **kwargs)
        
        