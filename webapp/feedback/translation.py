from modeltranslation.translator import register, TranslationOptions

from feedback.models import (
    ContentFeedbackQuestion,
    ThumbFeedbackQuestion,
    StarFeedbackQuestion,
    TextfieldFeedbackQuestion,
    MultipleChoiceFeedbackQuestion,
    MultipleChoiceFeedbackAnswer,
)


@register(ContentFeedbackQuestion)
class ContentFeedbackQuestionTranslationOptions(TranslationOptions):
    fields = ("question",)


@register(ThumbFeedbackQuestion)
class ThumbFeedbackQuestionTranslationOptions(TranslationOptions):
    fields = ("question",)


@register(StarFeedbackQuestion)
class StarFeedbackQuestionTranslationOptions(TranslationOptions):
    fields = ("question",)


@register(TextfieldFeedbackQuestion)
class TextfieldFeedbackQuestionTranslationOptions(TranslationOptions):
    fields = ("question",)


@register(MultipleChoiceFeedbackQuestion)
class MultipleChoiceFeedbackQuestionTranslationOptions(TranslationOptions):
    fields = ("question",)


@register(MultipleChoiceFeedbackAnswer)
class MultipleChoiceFeedbackAnswerTranslationOptions(TranslationOptions):
    fields = ("answer",)
