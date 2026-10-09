from modeltranslation.translator import register, TranslationOptions
from ace.models import AcePlusWidgetSettings

@register(AcePlusWidgetSettings)
class AcePlusWidgetSettingsTranslationOptions(TranslationOptions):
    fields = []

