from modeltranslation.translator import register, TranslationOptions

from courses.models import (
    About,
    CalendarDate,
    CheckboxExercise,
    CheckboxExerciseAnswer,
    ContentPage,
    Course,
    CourseInstance,
    CourseMedia,
    File,
    FileExerciseSettings,
    FileExerciseTestCommand,
    FileExerciseTestIncludeFile,
    FileExerciseTestStage,
    FileUploadExercise,
    Hint,
    Image,
    IncludeFileSettings,
    InstanceIncludeFile,
    Lecture,
    MultipleChoiceExercise,
    MultipleChoiceExerciseAnswer,
    RepeatedTemplateExercise,
    RepeatedTemplateExerciseBackendCommand,
    RepeatedTemplateExerciseTemplate,
    SavedMessage,
    Term,
    TermAlias,
    TermLink,
    TermTab,
    TermTag,
    TextfieldExercise,
    TextfieldExerciseAnswer,
    VideoLink,
)


## Generic


@register(SavedMessage)
class SavedMessageTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "content",
    )


@register(About)
class AboutTranslationOptions(TranslationOptions):
    fields = (
        "content",
    )

## Course related


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


@register(CourseInstance)
class CourseInstanceTranslationOptions(TranslationOptions):
    fields = ("name", "email", "notes", "welcome_message")


## Page content objects


@register(CourseMedia)
class CourseMediaTranslationOptions(TranslationOptions):
    pass


@register(File)
class FileTranslationOptions(TranslationOptions):
    fields = ("fileinfo", "download_as")


@register(Image)
class ImageTranslationOptions(TranslationOptions):
    fields = (
        "description",
        "fileinfo",
    )


@register(VideoLink)
class VideoLinkTranslationOptions(TranslationOptions):
    fields = (
        "link",
        "description",
    )


@register(Term)
class TermTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(TermTab)
class TermTabTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


@register(TermAlias)
class TermAliasTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(TermTag)
class TermTagTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(TermLink)
class TermLinkTranslationOptions(TranslationOptions):
    fields = (
        "url",
        "link_text",
    )


@register(CalendarDate)
class CalendarDateTranslationOptions(TranslationOptions):
    fields = (
        "event_name",
        "event_description",
    )


## Content pages - lectures and exercises


@register(ContentPage)
class ContentPageTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )


@register(Lecture)
class LectureTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
    )


@register(MultipleChoiceExercise)
class MultipleChoiceExerciseTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )


@register(CheckboxExercise)
class CheckboxExerciseTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )


@register(TextfieldExercise)
class TextfieldExerciseTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )


@register(FileUploadExercise)
class FileUploadExerciseTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )


@register(RepeatedTemplateExercise)
class RepeatedTemplateExerciseTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "content",
        "question",
    )


# @register(CodeInputExercise)
# class CodeInputExerciseTranslationOptions(TranslationOptions):
# fields = ('',)


## Exercise evaluation related objects


@register(Hint)
class HintTranslationOptions(TranslationOptions):
    fields = ("hint",)


@register(FileExerciseTestStage)
class FileExerciseTestStageTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(FileExerciseTestCommand)
class FileExerciseTestCommandTranslationOptions(TranslationOptions):
    fields = (
        "command_line",
        "input_text",
    )


@register(InstanceIncludeFile)
class InstanceIncludeFileTranslationOptions(TranslationOptions):
    fields = (
        "default_name",
        "description",
        "fileinfo",
    )


@register(FileExerciseTestIncludeFile)
class FileExerciseTestIncludeFileTranslationOptions(TranslationOptions):
    fields = (
        "default_name",
        "description",
        "fileinfo",
    )


@register(IncludeFileSettings)
class IncludeFileSettingsTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(TextfieldExerciseAnswer)
class TextfieldExerciseAnswerTranslationOptions(TranslationOptions):
    fields = (
        "answer",
        "hint",
        "comment",
    )


@register(MultipleChoiceExerciseAnswer)
class MultipleChoiceExerciseAnswerTranslationOptions(TranslationOptions):
    fields = (
        "answer",
        "hint",
        "comment",
    )


@register(CheckboxExerciseAnswer)
class CheckboxExerciseAnswerTranslationOptions(TranslationOptions):
    fields = (
        "answer",
        "hint",
        "comment",
    )


@register(RepeatedTemplateExerciseTemplate)
class RepeatedTemplateExerciseTemplateTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "content_string",
    )


@register(RepeatedTemplateExerciseBackendCommand)
class RepeatedTemplateExerciseBackendCommandTranslationOptions(TranslationOptions):
    fields = ("command",)

@register(FileExerciseSettings)
class FileExerciseSettingsTranslationOptions(TranslationOptions):
    fields = ("answer_filename",)
