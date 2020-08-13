from modeltranslation.translator import register, TranslationOptions

from .models import *

@register(RoutineExercise)
class RoutineExerciseTranslationOptions(TranslationOptions):
    fields = ("name", "content", "question",)

@register(RoutineExerciseTemplate)
class RoutineExerciseTemplateTranslationOptions(TranslationOptions):
    fields = ("content",)
    
@register(RoutineExerciseBackendCommand)
class RoutineExerciseBackendCommandTranslationOptions(TranslationOptions):
    fields = ("command",)

@register(RoutineExerciseProgress)
class RoutineExerciseProgressTranslationOptions(TranslationOptions):
    fields = ("progress",)