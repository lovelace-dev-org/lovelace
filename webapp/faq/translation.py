from modeltranslation.translator import register, TranslationOptions

from faq.models import FaqQuestion

@register(FaqQuestion)
class FaqQuestionTranslationOptions(TranslationOptions):
    fields = ("question", "answer")
