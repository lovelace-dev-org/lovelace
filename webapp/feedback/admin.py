from django.contrib import admin

from .models import TextfieldFeedbackQuestion, ThumbFeedbackQuestion, \
    StarFeedbackQuestion, MultipleChoiceFeedbackQuestion, MultipleChoiceFeedbackAnswer, \
    EmbeddedMultipleChoiceFeedbackQuestion, EmbeddedStarFeedbackQuestion, \
    EmbeddedThumbFeedbackQuestion, EmbeddedTextfieldFeedbackQuestion, \
    EmbeddedMultipleChoiceFeedbackAnswer

class MultipleChoiceFeedbackAnswerInline(admin.TabularInline):
    model = MultipleChoiceFeedbackAnswer

class TextfieldFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="TEXTFIELD_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    list_per_page = 500

class ThumbFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="THUMB_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    list_per_page = 500

class StarFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="STAR_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    list_per_page = 500

class MultipleChoiceFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="MULTIPLE_CHOICE_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")
    inlines = [MultipleChoiceFeedbackAnswerInline]
    list_per_page = 500

class EmbeddedMultipleChoiceFeedbackAnswerInline(admin.TabularInline):
    model = EmbeddedMultipleChoiceFeedbackAnswer

class EmbeddedTextfieldFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="TEXTFIELD_FEEDBACK")

    fields = ("question", "description")
    list_display = ("question", "slug")
    list_per_page = 500

class EmbeddedThumbFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="THUMB_FEEDBACK")

    fields = ("question", "description")
    list_display = ("question", "slug")
    list_per_page = 500

class EmbeddedStarFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="STAR_FEEDBACK")

    fields = ("question", "description")
    list_display = ("question", "slug")
    list_per_page = 500

class EmbeddedMultipleChoiceFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="MULTIPLE_CHOICE_FEEDBACK")

    fields = ("question", "description")
    list_display = ("question", "slug")
    inlines = [EmbeddedMultipleChoiceFeedbackAnswerInline]
    list_per_page = 500


admin.site.register(TextfieldFeedbackQuestion, TextfieldFeedbackQuestionAdmin)
admin.site.register(ThumbFeedbackQuestion, ThumbFeedbackQuestionAdmin)
admin.site.register(StarFeedbackQuestion, StarFeedbackQuestionAdmin)
admin.site.register(MultipleChoiceFeedbackQuestion, MultipleChoiceFeedbackQuestionAdmin)
admin.site.register(EmbeddedTextfieldFeedbackQuestion, EmbeddedTextfieldFeedbackQuestionAdmin)
admin.site.register(EmbeddedThumbFeedbackQuestion, EmbeddedThumbFeedbackQuestionAdmin)
admin.site.register(EmbeddedStarFeedbackQuestion, EmbeddedStarFeedbackQuestionAdmin)
admin.site.register(EmbeddedMultipleChoiceFeedbackQuestion, EmbeddedMultipleChoiceFeedbackQuestionAdmin)
