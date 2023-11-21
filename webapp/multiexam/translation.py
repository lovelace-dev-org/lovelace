from modeltranslation.translator import register, TranslationOptions

from multiexam.models import MultipleChoiceExam, ExamQuestionPool

@register(MultipleChoiceExam)
class MultipleChoiceExamTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )

@register(ExamQuestionPool)
class ExamQuestionPoolTranslationOptions(TranslationOptions):
    fields = (
        "fileinfo",
    )
