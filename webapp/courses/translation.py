from modeltranslation.translator import register, TranslationOptions

from courses.models import Course, CourseInstance, \
    \
    File, Image, VideoLink, CalendarDate, Term, \
    \
    ContentPage, Lecture, MultipleChoiceExercise, CheckboxExercise, \
    TextfieldExercise, CodeReplaceExercise, CodeInputExercise, \
    FileUploadExercise, \
    \
    Hint, FileExerciseTestStage, \
    TextfieldExerciseAnswer, MultipleChoiceExerciseAnswer, \
    CheckboxExerciseAnswer, CodeInputExerciseAnswer, \
    CodeReplaceExerciseAnswer


## Course related

@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)

@register(CourseInstance)
class CourseInstanceTranslationOptions(TranslationOptions):
    fields = ('name', 'notes')


## Page content objects

@register(File)
class FileTranslationOptions(TranslationOptions):
    fields = ('uploader', 'fileinfo',)

@register(Image)
class ImageTranslationOptions(TranslationOptions):
    fields = ('uploader', 'description', 'fileinfo',)

@register(VideoLink)
class VideoLinkTranslationOptions(TranslationOptions):
    fields = ('added_by', 'link', 'description',)

@register(Term)
class TermTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)

@register(CalendarDate)
class CalendarDateTranslationOptions(TranslationOptions):
    fields = ('event_name', 'event_description',)


## Content pages - lectures and exercises

@register(ContentPage)
class ContentPageTranslationOptions(TranslationOptions):
    fields = ('name', 'content', 'question',)

@register(Lecture)
class LectureTranslationOptions(TranslationOptions):
    fields = ('name', 'content',)

@register(MultipleChoiceExercise)
class MultipleChoiceExerciseTranslationOptions(TranslationOptions):
    fields = ('name', 'content', 'question',)

@register(CheckboxExercise)
class CheckboxExerciseTranslationOptions(TranslationOptions):
    fields = ('name', 'content', 'question',)

@register(TextfieldExercise)
class TextfieldExerciseTranslationOptions(TranslationOptions):
    fields = ('name', 'content', 'question',)

@register(FileUploadExercise)
class FileUploadExerciseTranslationOptions(TranslationOptions):
    fields = ('name', 'content', 'question',)

# TODO: Unfinished exercise types: deter until ready.

@register(CodeReplaceExercise)
class CodeReplaceExerciseTranslationOptions(TranslationOptions):
    fields = ('name', 'content', 'question',)

#@register(CodeInputExercise)
#class CodeInputExerciseTranslationOptions(TranslationOptions):
    #fields = ('',)


## Exercise evaluation related objects

@register(Hint)
class HintTranslationOptions(TranslationOptions):
    fields = ('hint',)

@register(FileExerciseTestStage)
class FileExerciseTestStageTranslationOptions(TranslationOptions):
    fields = ('name',)

# TODO: Other file exercise stuff: deter until pipeline overhaul done.

@register(TextfieldExerciseAnswer)
class TextfieldExerciseAnswerTranslationOptions(TranslationOptions):
    fields = ('answer', 'hint', 'comment',)

@register(MultipleChoiceExerciseAnswer)
class MultipleChoiceExerciseAnswerTranslationOptions(TranslationOptions):
    fields = ('answer', 'hint', 'comment',)

@register(CheckboxExerciseAnswer)
class CheckboxExerciseAnswerTranslationOptions(TranslationOptions):
    fields = ('answer', 'hint', 'comment',)

# TODO: Unfinished exercise types: deter until ready.

#@register(CodeInputExerciseAnswer)
#class CodeInputExerciseAnswerTranslationOptions(TranslationOptions):
    #fields = ('answer',)

#@register(CodeReplaceExerciseAnswer)
#class CodeReplaceExerciseAnswerTranslationOptions(TranslationOptions):
    #fields = ('answer',)




""" for easy copy paste:
@register()
class TranslationOptions(TranslationOptions):
    fields = ('',)
"""
