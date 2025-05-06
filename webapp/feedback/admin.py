from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline

from .models import (
    TextfieldFeedbackQuestion,
    ThumbFeedbackQuestion,
    StarFeedbackQuestion,
    MultipleChoiceFeedbackQuestion,
    MultipleChoiceFeedbackAnswer,
)


class MultipleChoiceFeedbackAnswerInline(TranslationTabularInline):
    model = MultipleChoiceFeedbackAnswer


class TextfieldFeedbackQuestionAdmin(TranslationAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="TEXTFIELD_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    list_per_page = 500


class ThumbFeedbackQuestionAdmin(TranslationAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="THUMB_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    list_per_page = 500


class StarFeedbackQuestionAdmin(TranslationAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="STAR_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    list_per_page = 500


class MultipleChoiceFeedbackQuestionAdmin(TranslationAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="MULTIPLE_CHOICE_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    inlines = [MultipleChoiceFeedbackAnswerInline]
    list_per_page = 500


admin.site.register(TextfieldFeedbackQuestion, TextfieldFeedbackQuestionAdmin)
admin.site.register(ThumbFeedbackQuestion, ThumbFeedbackQuestionAdmin)
admin.site.register(StarFeedbackQuestion, StarFeedbackQuestionAdmin)
admin.site.register(MultipleChoiceFeedbackQuestion, MultipleChoiceFeedbackQuestionAdmin)
