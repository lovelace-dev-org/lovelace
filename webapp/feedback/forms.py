from django.core.exceptions import ValidationError
from django import forms
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from utils.management import TranslationStaffForm

import courses.models as cm
from .models import (
    ContentFeedbackQuestion,
    TextfieldFeedbackQuestion,
    ThumbFeedbackQuestion,
    StarFeedbackQuestion,
    MultipleChoiceFeedbackQuestion,
    MultipleChoiceFeedbackAnswer,
)

class ContentFeedbackConfigForm(forms.ModelForm):

    class Meta:
        model = cm.ContentPage
        fields = ["feedback_questions"]


class FeedbackQuestionEditForm(TranslationStaffForm):

    class Meta:
        model = ContentFeedbackQuestion
        fields = ["question", "question_type"]


class MultipleChoiceFeedbackAnswerInline(TranslationStaffForm):

    class Meta:
        model = MultipleChoiceFeedbackAnswer
        fields = ["answer"]


class MultipleChoiceFeedbackEditForm(FeedbackQuestionEditForm):

    has_inline = True

    def management_form(self):
        return self._include_formset.management_form

    def empty_form(self):
        return self._include_formset.empty_form

    def get_inline_formset(self):
        return self._include_formset.forms

    def is_valid(self):
        if super().is_valid():
            if self._include_formset.is_valid():
                return True
        return False

    def save(self, commit=True):
        instance = super().save(commit=commit)
        self._include_formset.save()
        return instance

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        self._include_formset = forms.inlineformset_factory(
            MultipleChoiceFeedbackQuestion,
            MultipleChoiceFeedbackAnswer,
            form=TranslationStaffForm,
            fields=["answer"],
            extra=1
        )(
            args[0] if self.is_bound else None,
            instance=instance
        )



