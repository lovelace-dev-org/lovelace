import django.conf

from courses.models import *

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from django.core.cache import cache
from django.core.urlresolvers import reverse

from django.db import models, transaction
from django.db.models import Q
from django.forms import Field, ModelForm, TextInput, Textarea, ModelChoiceField

from .forms import FileEditForm, RepeatedTemplateExerciseBackendForm
from .widgets import AdminFileWidget, AdminTemplateBackendFileWidget

from modeltranslation.admin import TranslationAdmin, TranslationTabularInline, \
    TranslationStackedInline

from reversion.admin import VersionAdmin
from reversion.models import Version

## User profiles
# http://stackoverflow.com/questions/4565814/django-user-userprofile-and-admin
admin.site.unregister(User)

#TODO: There's a loophole where staff members of any course A can gain access
#      to any course B's pages by embedding the course B page to a course A 
#      page. The behavior itself is necessary to complete the access chain. 
#      Editors must be prohibited from adding embedded links to pages they do
#      not have access to. 
class CourseContentAccess(admin.ModelAdmin):
    """
    This class adds access control based on 1) authorship and 2) staff membership
    on the relevant course. Staff membership follows both contentgraph links and 
    embedded page links. 
    
    The entire access chain:
    Course
    -> CourseInstance
      -> ContentGraph
        -> ContentPage
          -> EmbeddedLink
            -> ContentPage
    """
    
    content_type = ""

    @staticmethod
    def content_access_list(request, model, content_type=None):
        """
        Gets a queryset of content where the requesting user either:
        1) has edited the page previously
        2) belongs to the staff of a course that contains the content
           either as a contentgraph node or as an embedded page
        
        The content type is read from the content_type attribute. Child
        classes should set this attribute to control which type of 
        content is shown.         
        """        
        
        if content_type:
            qs = model.objects.filter(content_type=content_type)
        else:
            qs = model.objects.all()
            
        if request.user.is_superuser:
            return qs
        
        edited = Version.objects.get_for_model(model).filter(revision__user=request.user).values_list("object_id", flat=True)
        
        return qs.filter(
            Q(id__in=list(edited)) |
            Q(contentgraph__courseinstance__course__staff_group__user=request.user) |
            Q(emb_embedded__parent__contentgraph__courseinstance__course__staff_group__user=request.user)
        ).distinct()

    def get_queryset(self, request):
        return CourseContentAccess.content_access_list(request, self.model, self.content_type)
    
    
    def has_change_permission(self, request, obj=None):        
        if request.user.is_superuser:
            return True
        
        if request.user.is_staff:
            if obj:
                return Version.objects.get_for_object(obj).filter(revision__user=request.user).exists() or self._match_groups(request.user, obj)
            else:            
                return True
        else:
            return False            
    
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        
        elif request.user.is_staff:
            if obj:
                return Version.objects.get_for_object(obj).filter(revision__user=request.user).exists() or self._match_groups(request.user, obj)
            else:            
                return True
        else:
            return False        
        
    #TODO: this solution is garbage, we need to rethink the entire content
    #      graph and embedded links structure. 
    def save_model(self, request, obj, form, change):
        """
        Need to call rendered_markup of the object for each context where it 
        exists in order to create embedded page links. 
        """
        
        super().save_model(request, obj, form, change)
        contexts = self._find_contexts(obj)
        for context in contexts:
            obj.rendered_markup(request, context)        
        
    def _find_contexts(self, obj):
        """
        Find the context(s) (course instances) where this page is linked. 
        """
        
        instances = CourseInstance.objects.filter(contents__content=obj)
        contexts = []
        for instance in instances:
            context = {
                'course': instance.course,
                'course_slug': instance.course.slug,
                'instance': instance,
                'instance_slug': instance.slug,
            }
            contexts.append(context)
        
        return contexts        

    def _match_groups(self, user, obj):
        """
        Matches a user's groups to the staff groups of the target object.
        Returns True if the user is in the staff group of the course that 
        is at the end of the access chain for the object.
        """
        
        if Course.objects.filter(
            Q(courseinstance__contents__content=obj) |
            Q(courseinstance__contents__content__embedded_pages=obj)
        ).filter(staff_group__user=user):
            return True
        
        return False


class CourseMediaAccess(admin.ModelAdmin):
    
    @staticmethod
    def media_access_list(request, model):
        qs = model.objects.all()
        
        if request.user.is_superuser:
            return qs
        
        user_groups = request.user.groups.get_queryset()
        
        return qs.filter(
            Q(owner=request.user) |
            Q(courseinstance__course__staff_group__in=user_groups)
        ).distinct()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'courseinstance':
            if not request.user.is_superuser:
                kwargs['queryset'] = CourseInstance.objects.filter(course__staff_group__user=request.user)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        return CourseMediaAccess.media_access_list(request, self.model)
    
    def has_change_permission(self, request, obj=None):        
        if request.user.is_superuser:
            return True
        
        if request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)
            else:            
                return True
        else:
            return False            
        
    def has_delete_permission(self, request, obj=None):        
        if request.user.is_superuser:
            return True
        
        if request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)
            else:            
                return True
        else:
            return False            

    def _match_groups(self, user, obj):
        user_groups = user.groups.get_queryset()
        return user in obj.courseinstance.course.staff_group.user_set.get_queryset()
        
    

class UserProfileInline(admin.StackedInline):
    model = UserProfile

class UserProfileAdmin(UserAdmin):
    inlines = [UserProfileInline,]

admin.site.register(User, UserProfileAdmin)

## Feedback for user answers
admin.site.register(Evaluation)

## Exercise types
# TODO: Create an abstract way to admin the different task types
#class AbstractQuestionAdmin(admin.ModelAdmin):
#    def save_model(self, request, obj, form, change):
#        obj.save()
#        if not change:
#            obj.users.add(request, user)
#
##    def queryset(self, request):
#        qs = super(AbstractQuestionAdmin, self).queryset(request)
#        if request.user.is_superuser:
#            return qs.select_subclasses()
#        return qs.select_subclasses().filter(users=request.user)

# TODO: How to link ContentFeedbackQuestion objects nicely?
class HintInline(TranslationTabularInline):
    model = Hint
    fk_name = 'exercise'
    extra = 0
    queryset = TranslationTabularInline.get_queryset

class MultipleChoiceExerciseAnswerInline(TranslationTabularInline):
    model = MultipleChoiceExerciseAnswer
    extra = 1

class MultipleChoiceExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "MULTIPLE_CHOICE_EXERCISE"
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="MULTIPLE_CHOICE_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags'],}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [MultipleChoiceExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class CheckboxExerciseAnswerInline(TranslationTabularInline):
    model = CheckboxExerciseAnswer
    extra = 1

class CheckboxExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "CHECKBOX_EXERCISE"
    
    #def get_queryset(self, request):
    #   return self.model.objects.filter(content_type="CHECKBOX_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CheckboxExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class TextfieldExerciseAnswerInline(TranslationStackedInline):
    model = TextfieldExerciseAnswer
    extra = 1

class TextfieldExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "TEXTFIELD_EXERCISE"
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="TEXTFIELD_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [TextfieldExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class CodeReplaceExerciseAnswerInline(admin.StackedInline):
    model = CodeReplaceExerciseAnswer
    extra = 1

class CodeReplaceExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "CODE_REPLACE_EXERCISE"
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="CODE_REPLACE_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CodeReplaceExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class RepeatedTemplateExerciseTemplateInline(TranslationStackedInline):
    model = RepeatedTemplateExerciseTemplate
    extra = 1

class RepeatedTemplateExerciseBackendFileInline(admin.StackedInline):
    model = RepeatedTemplateExerciseBackendFile
    extra = 1
    form = RepeatedTemplateExerciseBackendForm
    formfield_overrides = {
        models.FileField: {'widget': AdminTemplateBackendFileWidget}
    }

class RepeatedTemplateExerciseBackendCommandInline(TranslationStackedInline):
    model = RepeatedTemplateExerciseBackendCommand

class RepeatedTemplateExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):

    content_type = "REPEATED_TEMPLATE_EXERCISE"

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]

    inlines = [RepeatedTemplateExerciseTemplateInline, RepeatedTemplateExerciseBackendFileInline,
               RepeatedTemplateExerciseBackendCommandInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class FileExerciseTestCommandAdmin(admin.TabularInline):
    model = FileExerciseTestCommand
    extra = 1

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(FileExerciseTestCommandAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'command_line':
            formfield.widget = TextInput(attrs={'size':120})
        return formfield

class FileExerciseTestExpectedStdoutAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStdout
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

class FileExerciseTestExpectedStderrAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStderr
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

# class FileExerciseTestAdmin(admin.ModelAdmin):
#     fieldsets = (
#         ('General settings', {
#             'fields': ('task', 'name', 'inputs')
#         }),
#         ('Advanced settings', {
#             'classes': ('collapse',),
#             'fields': ('timeout', 'signals', 'retval')
#         }),
#     )
#     inlines = []
#     search_fields = ("name",)
#     list_display = ("name", "exercise")
#     list_per_page = 500
    
#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "exercise":
#             kwargs["queryset"] = FileUploadExercise.objects.order_by("name")
#         return super(FileExerciseTestAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

#class FileExerciseTestAdmin(admin.StackedInline):
#    inlines = [FileExerciseTestCommandAdmin, FileExerciseTestExpectedOutputAdmin, FileExerciseTestExpectedErrorAdmin, FileExerciseTestIncludeFileAdmin]

class LectureAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "LECTURE"
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(LectureAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'content':
            formfield.widget = Textarea(attrs={'rows':25, 'cols':120})
        elif db_field.name == 'tags':
            formfield.widget = Textarea(attrs={'rows':2})
        return formfield

    def view_on_site(self, obj):
        return reverse('courses:sandbox', kwargs={'content_slug': obj.slug})

    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

# Still required even though a custom admin is implemented
class FileUploadExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "FILE_UPLOAD_EXERCISE"
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="FILE_UPLOAD_EXERCISE")
    
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

admin.site.register(FileUploadExercise, FileUploadExerciseAdmin)

# TODO: Use the view_on_site on all content models!

admin.site.register(Lecture, LectureAdmin)
admin.site.register(MultipleChoiceExercise, MultipleChoiceExerciseAdmin)
admin.site.register(CheckboxExercise, CheckboxExerciseAdmin)
admin.site.register(TextfieldExercise, TextfieldExerciseAdmin)
admin.site.register(CodeReplaceExercise, CodeReplaceExerciseAdmin)
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

class FileAdmin(CourseMediaAccess):
    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        obj.save()

    search_fields = ('name',)
    readonly_fields = ('owner',)
    form = FileEditForm
    formfield_overrides = {
        models.FileField: {'widget': AdminFileWidget}
    }
        
    
    

class ImageAdmin(CourseMediaAccess):
    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        obj.save()

    search_fields = ('name',)
    readonly_fields = ('owner',)
    list_display = ('name', 'description',)
    list_per_page = 500

class VideoLinkAdmin(CourseMediaAccess):
    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        obj.save()

    search_fields = ('name',)
    readonly_fields = ('owner',)
    list_display = ('name', 'description',)
    list_per_page = 500

class TermTabInline(TranslationTabularInline):
    model = TermTab
    extra = 0

class TermLinkInline(TranslationTabularInline):
    model = TermLink
    extra = 0
    
class TermAdmin(TranslationAdmin, VersionAdmin):
    search_fields = ('name',)
    list_display = ('name', 'instance',)
    list_filter = ('instance',)
    list_per_page = 500
    ordering = ('name',)

    inlines = [TermTabInline, TermLinkInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        instance_slug = obj.instance.slug
        lang_list = django.conf.settings.LANGUAGES
        for lang, _ in lang_list:
            cache.set('termbank_contents_{instance}_{lang}'.format(instance=instance_slug, lang=lang), None)
            cache.set('termbank_div_data_{instance}_{lang}'.format(instance=instance_slug, lang=lang), None)

admin.site.register(Calendar, CalendarAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(VideoLink, VideoLinkAdmin)
admin.site.register(Term, TermAdmin)


## Course related administration
class ContentGraphAdmin(admin.ModelAdmin):
    
    search_fields = ('content',)
    list_display = ('ordinal_number', 'content', 'get_instances',)
    list_display_links = ('content',)
    list_filter = ('courseinstance',)
    list_per_page = 500
    ordering = ('courseinstance', 'ordinal_number',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit the queryset for content selector to pages that are in the 
        editor's access chain. 
        """
        
        if db_field.name == 'content':
            kwargs['queryset'] = CourseContentAccess.content_access_list(request, ContentPage)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
    def get_queryset(self, request):
        return super(ContentGraphAdmin, self).get_queryset(request)
    
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)            
            else:
                return True
        else:
            return False
        
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)
            else:
                return True
        else:
            return False
        
    def _match_groups(self, user, obj):
        user_groups = user.groups.get_queryset()
        
        if Course.objects.filter(courseinstance__contents=obj).filter(staff_group__in=user_groups):
            return True
        
        return False

    def get_instances(self, obj):
        return " | ".join([i.name for i in obj.courseinstance_set.all()])
    
    get_instances.short_description = "Instances"

admin.site.register(ContentGraph, ContentGraphAdmin)

class CourseAdmin(TranslationAdmin, VersionAdmin):
    fieldsets = [
        (None,             {'fields': ['name', 'slug',]}),
        ('Course outline', {'fields': ['description', 'code', 'credits']}),
        ('Administration', {'fields': ['staff_group', 'main_responsible']}),
        #('Settings for start date and end date of the course', {'fields': ['start_date','end_date'], 'classes': ['collapse']}),
    ]
    #formfield_overrides = {models.ManyToManyField: {'widget':}}
    search_fields = ('name',)
    readonly_fields = ('slug',)

admin.site.register(Course, CourseAdmin)

class CourseInstanceAdmin(TranslationAdmin, VersionAdmin):
    """
    NOTE: Only the user designated as main responsible for a course is 
    allowed to create instances of the course, and to include content 
    graphs to an instance. 
    """    
    
    fieldsets = [
        (None,                {'fields': ['name', 'email', 'course', 'frontpage']}),
        ('Schedule settings', {'fields': ['start_date', 'end_date', 'active',]}),
        ('Enrollment',        {'fields': ['manual_accept']}),
        ('Instance outline',  {'fields': ['contents',]}),
    ]
    search_fields = ('name',)
    list_display = ('name', 'course')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Only show courses where the editor is marked as main responsible. 
        """
        
        if db_field.name == 'course':
            if not request.user.is_superuser:
                kwargs['queryset'] = Course.objects.filter(main_responsible=request.user)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)                                                
        
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Only show content graphs that contain content that is in the editor's
        access chain.
        """
        
        if db_field.name == 'contents':           
            content_access = CourseContentAccess.content_access_list(request, ContentPage)
            kwargs['queryset'] = ContentGraph.objects.filter(content__in=content_access)
            
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        return qs.filter(course__main_responsible=request.user)
        
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return obj.course.main_responsible == request.user
            else:
                return True
        else:
            return False
        
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return obj.course.main_responsible == request.user
            else:
                return True
        else:
            return False
        
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        context = {
            'course': obj.course,
            'course_slug': obj.course.slug,
            'instance': obj,
            'instance_slug': obj.slug,
        }
        
        for cg in obj.contents.all():
            cg.content.rendered_markup(request, context)
            
        self.current = obj
        transaction.on_commit(self.set_frontpage_cg)
            
    # the horror
    def set_frontpage_cg(self): 
        obj = self.current
        if obj.frontpage:
            fp_node = ContentGraph.objects.filter(courseinstance=obj.id, ordinal_number=0).first()
            if fp_node:
                fp_node.content = obj.frontpage
                fp_node.save()
            else:
                fp_node = obj.contents.create(
                    content=obj.frontpage,
                    scored=False,
                    ordinal_number=0
                )
            
admin.site.register(CourseInstance, CourseInstanceAdmin)
