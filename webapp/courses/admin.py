import django.conf
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Q, Prefetch
from django.forms import BaseInlineFormSet, TextInput

from modeltranslation.admin import (
    TranslationAdmin,
    TranslationTabularInline,
    TranslationStackedInline,
)

from reversion.admin import VersionAdmin
from reversion.models import Version
from reversion import revisions as reversion

from courses.models import (
    About,
    Calendar,
    CalendarDate,
    CheckboxExercise,
    CheckboxExerciseAnswer,
    ContentGraph,
    ContentPage,
    Course,
    CourseInstance,
    CourseMedia,
    File,
    FileUploadExercise,
    FileExerciseTest,
    FileExerciseTestStage,
    FileExerciseTestCommand,
    FileExerciseTestExpectedOutput,
    FileExerciseTestExpectedStderr,
    FileExerciseTestExpectedStdout,
    FileExerciseTestIncludeFile,
    Group,
    Hint,
    Image,
    InstanceIncludeFile,
    InstanceIncludeFileToExerciseLink,
    InstanceIncludeFileToInstanceLink,
    IncludeFileSettings,
    Lecture,
    MultipleChoiceExercise,
    MultipleChoiceExerciseAnswer,
    RepeatedTemplateExercise,
    RepeatedTemplateExerciseBackendCommand,
    RepeatedTemplateExerciseBackendFile,
    RepeatedTemplateExerciseTemplate,
    Term,
    TermAlias,
    TermLink,
    TermTab,
    TermTag,
    TermToInstanceLink,
    TextfieldExercise,
    TextfieldExerciseAnswer,
    UserProfile,
    VideoLink,
)
from courses.forms import (
    FileEditForm,
    ExerciseBackendForm,
    ContentForm,
    TextfieldAnswerForm,
    InstanceForm,
)
from courses.widgets import AdminFileWidget, AdminTemplateBackendFileWidget
from utils.management import CourseContentAdmin, CourseMediaAdmin

from faq.utils import clone_faq_links

# Moved these here from models.py so that all registering happens
# in this file (as VersionAdmin autoregisters the associated model)
# This makes modeltranslation work with reversion, probably due
# to translated fields being added between loading models.py and
# this module.
reversion.register(
    ContentPage,
    follow=[
        "checkboxexerciseanswer_set",
        "fileexercisetest_set",
        "fileexercisetestincludefile_set",
        "hint_set",
        "instanceincludefiletoexerciselink_set",
        "multiplechoiceexerciseanswer_set",
        "repeatedtemplateexercisebackendfile_set",
        "repeatedtemplateexercisetemplate_set",
        "textfieldexerciseanswer_set",
        "routineexercisetemplate_set",
        "routineexercisebackendfile_set",
        "routineexercisebackendcommand",
    ],
)
reversion.register(
    FileExerciseTest,
    follow=["fileexerciseteststage_set", "required_files", "required_instance_files"],
)
reversion.register(FileExerciseTestStage, follow=["fileexercisetestcommand_set"])
reversion.register(FileExerciseTestCommand, follow=["fileexercisetestexpectedoutput_set"])
reversion.register(FileExerciseTestExpectedOutput)
reversion.register(FileExerciseTestExpectedStdout)
reversion.register(FileExerciseTestExpectedStderr)
reversion.register(InstanceIncludeFileToExerciseLink)
reversion.register(InstanceIncludeFile)
reversion.register(FileExerciseTestIncludeFile)
reversion.register(IncludeFileSettings)
reversion.register(CourseMedia)
reversion.register(TermTab)
reversion.register(TermLink)
reversion.register(RepeatedTemplateExerciseTemplate)
reversion.register(RepeatedTemplateExerciseBackendFile)
reversion.register(RepeatedTemplateExerciseBackendCommand)


## User profiles
# http://stackoverflow.com/questions/4565814/django-user-userprofile-and-admin
admin.site.unregister(User)
admin.site.unregister(Group)


class AboutAdmin(TranslationAdmin):
    model = About


class UserProfileInline(admin.StackedInline):
    model = UserProfile


class UserProfileAdmin(UserAdmin):
    inlines = [
        UserProfileInline,
    ]


admin.site.register(About, AboutAdmin)
admin.site.register(User, UserProfileAdmin)


class CopyingGroupAdmin(GroupAdmin):
    save_as = True


admin.site.register(Group, CopyingGroupAdmin)


class HintInline(TranslationTabularInline):
    model = Hint
    fk_name = "exercise"
    extra = 0


class SoftDeleteFormSet(BaseInlineFormSet):
    def delete_existing(self, obj, commit=True):
        if commit:
            obj.exercise = None
            obj.save()


class MultipleChoiceExerciseAnswerInline(TranslationTabularInline):
    model = MultipleChoiceExerciseAnswer
    extra = 1
    formset = SoftDeleteFormSet
    ordering = ("ordinal",)


class MultipleChoiceExerciseAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):
    change_form_template = "courses/admin-multiple-choice.html"

    content_type = "MULTIPLE_CHOICE_EXERCISE"
    form = ContentForm

    fieldsets = [
        (
            "Page information",
            {
                "fields": ["name", "origin", "slug", "content", "question", "tags"],
            },
        ),
        (
            "Exercise miscellaneous",
            {
                "fields": [
                    "default_points",
                    "evaluation_group",
                    "delayed_evaluation",
                    "answer_limit",
                ],
                "classes": ["wide"],
            },
        ),
        ("Feedback settings", {"fields": ["feedback_questions"]}),
    ]
    inlines = [MultipleChoiceExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True
    save_as = True


class CheckboxExerciseAnswerInline(TranslationTabularInline):
    model = CheckboxExerciseAnswer
    extra = 1
    formset = SoftDeleteFormSet
    ordering = ("ordinal",)


class CheckboxExerciseAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):
    change_form_template = "courses/admin-checkbox.html"

    content_type = "CHECKBOX_EXERCISE"
    form = ContentForm

    fieldsets = [
        (
            "Page information",
            {
                "fields": ["name", "origin", "slug", "content", "question", "tags"],
            },
        ),
        (
            "Exercise miscellaneous",
            {
                "fields": [
                    "default_points",
                    "evaluation_group",
                    "delayed_evaluation",
                    "answer_limit",
                ],
                "classes": ["wide"],
            },
        ),
        ("Feedback settings", {"fields": ["feedback_questions"]}),
    ]
    inlines = [CheckboxExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True
    save_as = True


class TextfieldExerciseAnswerInline(TranslationStackedInline):
    model = TextfieldExerciseAnswer
    extra = 1
    form = TextfieldAnswerForm
    fields = ["correct", "regexp", "answer", "hint", "comment"]


class TextfieldExerciseAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):
    change_form_template = "courses/admin-textfield.html"

    content_type = "TEXTFIELD_EXERCISE"
    form = ContentForm

    fieldsets = [
        (
            "Page information",
            {
                "fields": ["name", "origin", "slug", "content", "question", "tags"],
            },
        ),
        (
            "Exercise miscellaneous",
            {
                "fields": [
                    "default_points",
                    "answer_limit",
                    "manually_evaluated",
                    "delayed_evaluation",
                    "group_submission",
                    "evaluation_group",
                ],
                "classes": ["wide"],
            },
        ),
        ("Feedback settings", {"fields": ["feedback_questions"]}),
    ]
    inlines = [TextfieldExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True


class RepeatedTemplateExerciseTemplateInline(TranslationStackedInline):
    model = RepeatedTemplateExerciseTemplate
    extra = 1


class RepeatedTemplateExerciseBackendFileInline(admin.StackedInline):
    model = RepeatedTemplateExerciseBackendFile
    extra = 1
    form = ExerciseBackendForm
    formfield_overrides = {models.FileField: {"widget": AdminTemplateBackendFileWidget}}


class RepeatedTemplateExerciseBackendCommandInline(TranslationStackedInline):
    model = RepeatedTemplateExerciseBackendCommand


class RepeatedTemplateExerciseAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):
    content_type = "REPEATED_TEMPLATE_EXERCISE"
    form = ContentForm

    fieldsets = [
        (
            "Page information",
            {"fields": ["name", "slug", "content", "question", "tags"]},
        ),
        (
            "Exercise miscellaneous",
            {"fields": ["default_points", "evaluation_group"], "classes": ["wide"]},
        ),
        ("Feedback settings", {"fields": ["feedback_questions"]}),
    ]

    inlines = [
        RepeatedTemplateExerciseTemplateInline,
        RepeatedTemplateExerciseBackendFileInline,
        RepeatedTemplateExerciseBackendCommandInline,
        HintInline,
    ]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True


class FileExerciseTestCommandAdmin(admin.TabularInline):
    model = FileExerciseTestCommand
    extra = 1

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "command_line":
            formfield.widget = TextInput(attrs={"size": 120})
        return formfield


class FileExerciseTestExpectedStdoutAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStdout
    extra = 0
    fields = (("expected_answer", "hint"), "correct", "regexp", "videohint")


class FileExerciseTestExpectedStderrAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStderr
    extra = 0
    fields = (("expected_answer", "hint"), "correct", "regexp", "videohint")


class LectureAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):
    change_form_template = "courses/admin-lecture.html"

    content_type = "LECTURE"
    form = ContentForm
    fieldsets = [
        ("Page information", {"fields": ["name", "content", "origin"]}),
        ("Feedback", {"fields": ["feedback_questions"]}),
    ]

    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True


# Still required even though a custom admin is implemented
class FileUploadExerciseAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):
    content_type = "FILE_UPLOAD_EXERCISE"
    form = ContentForm

    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500

    def reversion_register(self, model, **options):
        options["follow"] = (
            "fileexercisetest_set",
            "instanceincludefiletoexerciselink_set",
            "fileexercisetestincludefile_set",
        )
        super().reversion_register(model, **options)


admin.site.register(FileUploadExercise, FileUploadExerciseAdmin)

admin.site.register(Lecture, LectureAdmin)
admin.site.register(MultipleChoiceExercise, MultipleChoiceExerciseAdmin)
admin.site.register(CheckboxExercise, CheckboxExerciseAdmin)
admin.site.register(TextfieldExercise, TextfieldExerciseAdmin)
# admin.site.register(CodeReplaceExercise, CodeReplaceExerciseAdmin)
admin.site.register(RepeatedTemplateExercise, RepeatedTemplateExerciseAdmin)

admin.site.register(FileExerciseTestIncludeFile)
admin.site.register(InstanceIncludeFile)
admin.site.register(IncludeFileSettings)


## Page embeddable objects
class CalendarDateAdmin(admin.StackedInline):
    model = CalendarDate
    extra = 1


class CalendarAdmin(admin.ModelAdmin):
    inlines = [CalendarDateAdmin]
    search_fields = ("name",)


class FileAdmin(CourseMediaAdmin, TranslationAdmin, VersionAdmin):
    search_fields = ("name",)
    readonly_fields = ("slug",)
    form = FileEditForm
    formfield_overrides = {models.FileField: {"widget": AdminFileWidget}}


class ImageAdmin(CourseMediaAdmin, TranslationAdmin, VersionAdmin):
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "description",
    )
    list_per_page = 500


class VideoLinkAdmin(CourseMediaAdmin, TranslationAdmin, VersionAdmin):
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "description",
    )
    list_per_page = 500


class TermTabInline(TranslationTabularInline):
    model = TermTab
    extra = 0


class TermLinkInline(TranslationTabularInline):
    model = TermLink
    extra = 0


class TermAliasInline(TranslationTabularInline):
    model = TermAlias
    extra = 0


class TermAdmin(TranslationAdmin, VersionAdmin):
    search_fields = ("name",)
    list_display = (
        "name",
        "origin",
    )
    readonly_fields = ("slug",)
    list_filter = ("origin",)
    list_per_page = 500
    ordering = ("name",)

    inlines = [TermAliasInline, TermTabInline, TermLinkInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        edited = (
            Version.objects.get_for_model(Term)
            .filter(revision__user=request.user)
            .values_list("object_id", flat=True)
        )

        return qs.filter(
            Q(id__in=list(edited)) | Q(origin__staff_group__user=request.user)
        ).distinct()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            if obj:
                return (
                    Version.objects.get_for_object(obj).filter(revision__user=request.user).exists()
                    or request.user in obj.origin.staff_group.user_set.get_queryset()
                )
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            if obj:
                return (
                    Version.objects.get_for_object(obj).filter(revision__user=request.user).exists()
                    or request.user in obj.origin.staff_group.user_set.get_queryset()
                )
            return True
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        lang_list = django.conf.settings.LANGUAGES
        for instance in CourseInstance.objects.filter(course=obj.origin, frozen=False):
            instance_slug = instance.slug
            for lang, __ in lang_list:
                cache.set(
                    f"termbank_contents_{instance_slug}_{lang}",
                    None,
                    timeout=None,
                )
                cache.set(
                    f"termbank_div_data_{instance_slug}_{lang}",
                    None,
                    timeout=None,
                )


class TermTagAdmin(TranslationAdmin):
    pass


admin.site.register(Calendar, CalendarAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(VideoLink, VideoLinkAdmin)
admin.site.register(Term, TermAdmin)
admin.site.register(TermTag, TermTagAdmin)


## Course related administration
class ContentGraphAdmin(admin.ModelAdmin):
    search_fields = ("content__name",)
    list_display = (
        "ordinal_number",
        "content",
        "instance",
    )
    list_display_links = ("content",)
    list_filter = ("instance",)
    list_per_page = 500
    ordering = (
        "instance",
        "ordinal_number",
    )

    fields = (
        "parentnode",
        "content",
        "deadline",
        "scored",
        "ordinal_number",
        "visible",
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit the queryset for content selector to pages that are in the
        editor's access chain.
        """

        if db_field.name == "content":
            kwargs["queryset"] = CourseContentAdmin.content_access_list(request, ContentPage)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)
            return True
        return False

    def _match_groups(self, user, obj):
        return user in obj.instance.course.staff_group.user_set.get_queryset()

    def get_instances(self, obj):
        return " | ".join([i.name for i in obj.courseinstance_set.all()])

    get_instances.short_description = "Instances"


admin.site.register(ContentGraph, ContentGraphAdmin)


class CourseAdmin(TranslationAdmin, VersionAdmin):
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "slug",
                    "prefix",
                ]
            },
        ),
        ("Course outline", {"fields": ["description", "code", "credits"]}),
        (
            "Administration",
            {"fields": ["staff_group", "main_responsible", "staff_course"]},
        ),
    ]
    search_fields = ("name",)
    readonly_fields = ("slug",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Only show courses where the editor is marked as main responsible.
        """

        if db_field.name == "main_responsible":
            kwargs["queryset"] = User.objects.filter(is_staff=True).order_by("username")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Course, CourseAdmin)


class AllMethodCachingQueryset(models.query.QuerySet):
    def all(self, get_from_cache=True):
        if get_from_cache:
            return self
        return self._clone()


class AllMethodCachingManager(models.Manager):
    def get_query_set(self):
        return AllMethodCachingQueryset(self.model, using=self._db)


ContentGraph.cache_all_method = AllMethodCachingManager()
ContentPage.cache_all_method = AllMethodCachingManager()


class ContentGraphInline(admin.TabularInline):
    model = ContentGraph
    extra = 0
    fields = (
        "parentnode",
        "content",
        "deadline",
        "scored",
        "ordinal_number",
        "visible",
        "revision",
    )
    readonly_fields = ("revision",)
    ordering = ("ordinal_number",)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj)
        # use cached queryset
        formset.form.base_fields["parentnode"].queryset = kwargs["accessible_graphs"]
        formset.form.base_fields["content"].queryset = kwargs["accessible_pages"]

        # force preload choices
        formset.form.base_fields["parentnode"].choices = formset.form.base_fields[
            "parentnode"
        ].choices
        formset.form.base_fields["content"].choices = formset.form.base_fields["content"].choices
        return formset


class CourseInstanceAdmin(TranslationAdmin, VersionAdmin):
    """
    NOTE: Only the user designated as main responsible for a course is
    allowed to create instances of the course, and to include content
    graphs to an instance.
    """

    fieldsets = [
        (None, {"fields": ["name", "email", "course", "frontpage", "notes"]}),
        (
            "Schedule settings",
            {"fields": ["start_date", "end_date", "active", "visible", "primary"]},
        ),
        ("Enrollment", {"fields": ["manual_accept", "welcome_message"]}),
        ("Content license", {"fields": ["content_license", "license_url"]}),
        ("Instance outline", {"fields": ["frozen"]}),
    ]
    search_fields = ("name",)
    list_display = ("name", "course")
    save_as = True
    form = InstanceForm

    inlines = [ContentGraphInline]

    def add_view(self, request, form_url="", extra_context=None):
        """
        Prefetch accessible pages and their corresponding content graphs to
        limit what is shown under the content to course links in selectors.

        Accessible graphs has to include graphs from all instances.
        """

        content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
        self._accessible_pages = content_access.defer("content")
        self._accessible_graphs = ContentGraph.objects.filter(content__in=content_access)
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """
        Prefetch accessible pages and their corresponding content graphs to
        limit what is shown under the content to course links in selectors.
        """

        content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
        self._accessible_pages = content_access.defer("content").all()
        self._accessible_graphs = ContentGraph.objects.prefetch_related(
            Prefetch("content", queryset=self._accessible_pages)
        ).filter(content__in=content_access, instance__id=object_id)
        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Only show courses where the editor is marked as main responsible.
        """

        if db_field.name == "course":
            if not request.user.is_superuser:
                kwargs["queryset"] = Course.objects.filter(main_responsible=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Only show content graphs that contain content that is in the editor's
        access chain.
        """

        if db_field.name == "contents":
            content_access = CourseContentAdmin.content_access_list(request, ContentPage)
            kwargs["queryset"] = ContentGraph.objects.filter(content__in=content_access)

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_formsets_with_inlines(self, request, obj=None):
        """
        Limits the selectors inside inlines to content pages that are in the editor's
        access chain. Also limits parent node selector to nodes that belong to the same
        instance.
        """

        extra_kw = {
            "accessible_pages": self._accessible_pages,
            "accessible_graphs": self._accessible_graphs,
        }

        for inline in self.get_inline_instances(request, obj):
            if isinstance(inline, ContentGraphInline):
                yield inline.get_formset(request, obj, **extra_kw), inline
            else:
                yield inline.get_formset(request, obj), inline

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(course__main_responsible=request.user)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if request.user.is_staff:
            if obj:
                return obj.course.main_responsible == request.user
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if request.user.is_staff:
            if obj:
                return obj.course.main_responsible == request.user
            return True
        return False

    def save_model(self, request, obj, form, change):
        self._new = False
        if obj.pk is None:
            self._new = True

        super().save_model(request, obj, form, change)

        if self._new:
            instance_files = InstanceIncludeFile.objects.filter(course=obj.course)
            for ifile in instance_files:
                link = InstanceIncludeFileToInstanceLink(
                    revision=None, include_file=ifile, instance=obj
                )
                link.save()

            terms = Term.objects.filter(origin=obj.course)
            for term in terms:
                link = TermToInstanceLink(revision=None, term=term, instance=obj)
                link.save()

            clone_faq_links(obj)

        self.current = obj
        transaction.on_commit(self.finish_cg)

    # the horror
    def finish_cg(self):
        obj = self.current
        if obj.frontpage:
            fp_node = ContentGraph.objects.filter(instance=obj, ordinal_number=0).first()
            if fp_node and not self._new:
                fp_node.content = obj.frontpage
                fp_node.save()
            else:
                if fp_node:
                    fp_node.delete()
                fp_node = ContentGraph(
                    content=obj.frontpage, instance=obj, scored=False, ordinal_number=0
                )
                fp_node.save()

        if self._new:
            children = ContentGraph.objects.filter(instance=obj).exclude(parentnode=None)
            for child in children:
                real_parent = ContentGraph.objects.get(
                    content=child.parentnode.content, instance=obj
                )
                child.parentnode = real_parent
                child.save()

        if not obj._was_frozen and obj.frozen:
            obj._was_frozen = True
            obj.freeze()
        else:
            for cg in ContentGraph.objects.filter(instance=obj):
                cg.content.update_embedded_links(obj, cg.revision)


admin.site.register(CourseInstance, CourseInstanceAdmin)
