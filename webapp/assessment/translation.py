from modeltranslation.translator import register, TranslationOptions

from assessment.models import *

@register(AssessmentSheet)
class AssessmentSheetTranslationOptions(TranslationOptions):
    fields = ("title",)
    
@register(AssessmentBullet)
class AssessmentBulletTranslationOptions(TranslationOptions):
    fields = ("section", "title", "tooltip")