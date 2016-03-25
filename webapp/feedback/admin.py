from django.contrib import admin

from .models import TextfieldFeedbackQuestion, ThumbFeedbackQuestion, StarFeedbackQuestion

class TextfieldFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="TEXTFIELD_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")

class ThumbFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="THUMB_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")

class StarFeedbackQuestionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(question_type="STAR_FEEDBACK")

    fields = ("question",)
    list_display = ("question", "slug")

admin.site.register(TextfieldFeedbackQuestion, TextfieldFeedbackQuestionAdmin)
admin.site.register(ThumbFeedbackQuestion, ThumbFeedbackQuestionAdmin)
admin.site.register(StarFeedbackQuestion, StarFeedbackQuestionAdmin)
