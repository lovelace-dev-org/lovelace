from modeltranslation.translator import register, TranslationOptions

from multiexam.models import MultipleQuestionExam, ExamQuestionPool

@register(MultipleQuestionExam)
class MultipleQuestionExamTranslationOptions(TranslationOptions):
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
