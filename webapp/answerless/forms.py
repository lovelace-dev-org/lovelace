from django import forms
from django.forms import fields
from django.utils.translation import gettext_lazy as _

from utils.formatters import display_name
from utils.management import TranslationStaffForm

import courses.models as cm

from .models import AnswerlessEntry


class StudentEntryForm(forms.Form):

    def clean_user(self):
        user_id = self.cleaned_data.get("user")
        try:
            user = cm.User.objects.get(id=user_id)
        except cm.User.DoesNotExist:
            self.add_error("user", _("User is not enrolled"))
            return None
        return user

    def __init__(self, *args, **kwargs):
        students = kwargs.pop("students")
        super().__init__(*args, **kwargs)

        self.fields["user"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose student"),
            choices=[(s.id, display_name(s)) for s in students],
        )
        self.fields["quotient"] = forms.FloatField(
            max_value=1
        )
        self.fields["note"] = forms.CharField(required=False)
