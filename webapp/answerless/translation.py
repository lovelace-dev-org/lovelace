from modeltranslation.translator import register, TranslationOptions

from answerless.models import AnswerlessTask

@register(AnswerlessTask)
class AnswerlessTaskTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )
