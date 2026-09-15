from modeltranslation.translator import register, TranslationOptions

from . models import ExamTask

@register(ExamTask)
class ExamTaskTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )

