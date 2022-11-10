from django.conf import settings
from django.contrib import admin
from django.db.models import Q
from django.db import models, transaction
from django import forms
from django.forms import Textarea, ModelForm
from django.utils.translation import gettext as _
from reversion.models import Version
from modeltranslation.fields import TranslationField
from modeltranslation.translator import translator
from courses.models import Course, CourseInstance, ContentPage, ContentGraph,\
    InstanceIncludeFile, Term, TermToInstanceLink, InstanceIncludeFileToInstanceLink
from courses.widgets import ContentPreviewWidget
from utils.access import determine_access, determine_media_access


#TODO: There's a loophole where staff members of any course A can gain access
#      to any course B's pages by embedding the course B page to a course A 
#      page. The behavior itself is necessary to complete the access chain. 
#      Editors must be prohibited from adding embedded links to pages they do
#      not have access to. 
class CourseContentAdmin(admin.ModelAdmin):
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
        
        qs = qs.filter(
            Q(id__in=list(edited)) |
            Q(contentgraph__instance__course__staff_group__user=request.user) |
            Q(emb_embedded__parent__contentgraph__instance__course__staff_group__user=request.user)
        ).distinct()
        
        return qs

    def get_queryset(self, request):
        return CourseContentAdmin.content_access_list(request, self.model, self.content_type).defer("content")
    
    def has_add_permission(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return False
    
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_access(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_access(request.user, obj)
        
    #TODO: this solution is less garbage now, but we still need to rethink
    #      the entire contentgraph and embedded links structure. 
    #NOTE: this is now done in ContentPage save method
    #def save_model(self, request, obj, form, change):
        #"""
        #Need to call rendered_markup of the object for each context where it 
        #exists as latest version in order to create embedded page links. 
        #"""
        
        #super().save_model(request, obj, form, change)
        #contexts = self._find_contexts(obj)
        #for context in contexts:
            #obj.update_embedded_links(context["instance"])
        
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """
        Sets widgets for content and tags fields. Content in particular gets
        the preview widget which is capable of showing a rendered preview
        without saving the content first.
        """
        
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ('content'):
            formfield.widget = ContentPreviewWidget(attrs={'rows':25, 'cols':120})
        elif db_field.name == 'tags':
            formfield.widget = Textarea(attrs={'rows':2})
        return formfield
        
    def save_model(self, request, obj, form, change):
        """
        Sets the post_save method to be called after transaction commit when
        the model is saved.
        """
        
        super().save_model(request, obj, form, change)
        self.current = obj
        transaction.on_commit(self.post_save)
        
    def post_save(self):
        """
        When any type of content is saved, any associated cached data needs to
        be regenerated. As caching is done per lecture page, this will either
        regenerate cache for the page itself if it was a lecture, or for the
        parent if the page was an embedded task.
        """
        
        parents = ContentPage.objects.filter(embedded_pages=self.current).distinct()
        for instance in CourseInstance.objects.filter(Q(contentgraph__content=self.current) | Q(contentgraph__content__embedded_pages=self.current), frozen=False).distinct():
            self.current.update_embedded_links(instance)
            if self.current.content_type == "LECTURE":
                self.current.regenerate_cache(instance)
            for parent in parents:
                parent.regenerate_cache(instance)
        
    def _find_contexts(self, obj):
        """
        Find the context(s) (course instances) where this page is linked that 
        have not been frozen. 
        """
        
        instances = CourseInstance.objects.filter(contents__content=obj, contents__revision=None)
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
        


class CourseMediaAdmin(admin.ModelAdmin):
    
    @staticmethod
    def media_access_list(request, model):
        qs = model.objects.all()
        
        if request.user.is_superuser:
            return qs
        
        
        edited = Version.objects.get_for_model(model).filter(revision__user=request.user).values_list("object_id", flat=True)
        
        user_groups = request.user.groups.get_queryset()
        
        return qs.filter(
            Q(id__in=list(edited)) |
            Q(coursemedialink__instance__course__staff_group__in=user_groups)
        ).distinct()
    
    def get_queryset(self, request):
        return CourseMediaAdmin.media_access_list(request, self.model)
    
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_media_access(request.user, obj)
        
    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_media_access(request.user, obj)

    def _match_groups(self, user, obj):
        
        user_groups = user.groups.get_queryset()
        if obj.coursemedialink_set.get_queryset().filter(instance__course__staff_group__in=user_groups).distinct():
            return True
        
        return False

class DefaultFirstTranslationForm(ModelForm):

    pass

        
def clone_instance_files(instance):
    """
    Creates cloned links to all instance files in a course instance.
    """

    instance_files = InstanceIncludeFile.objects.filter(course=instance.course)
    for ifile in instance_files:
        link = InstanceIncludeFileToInstanceLink(
            revision=None,
            include_file=ifile,
            instance=instance
        )
        link.save()
        
def clone_terms(instance):
    """
    Creates cloned links to all terms in a course instance.
    """

    terms = Term.objects.filter(course=instance.course)
    for term in terms:
        link = TermToInstanceLink(
            revision=None,
            term=term,
            instance=instance
        )
        link.save()
    
def clone_grades(old_instance, new_instance):

    grades = GradeThreshold.filter(instance=old_instance)
    for grade in grades:
        grade.pk = None
        grade.instance = new_instance
        grade.save()


def clone_content_graphs(old_instance, new_instance):
    """
    Creates cloned links to all content nodes in a course instance. This is
    done in two passes. First all nodes are copied, and then the parents nodes
    are set updated to point to the matching cloned node.
    """

    content_graphs = ContentGraph.objects.filter(instance=old_instance)
    for graph in content_graphs:
        graph.pk = None
        graph.instance = new_instance
        graph.save()
        graph.content.update_embedded_links(new_instance, graph.revision)
        
    for child_node in ContentGraph.objects.filter(instance=new_instance).exclude(parentnode=None):
        new_parent = ContentGraph.objects.get(
            content=child_node.parentnode.content,
            instance=new_instance
        )
        child_node.parentnode = new_parent
        child_node.save()
    
def add_translated_charfields(form, field_name, default_label, alternative_label, require_default=True):
    """
    Adds charfields to a form for all languages. Used in generating many admin
    forms. Will treat MODELTRANSLATION_DEFAULT_LANGUAGE as the primary language
    and other languages as secondary that are always optional. The primary can
    be set to optional for fields that are optional. Labels need to be given
    separately for the default field, and for alternative fields.
    """
    
    languages = sorted(
        settings.LANGUAGES,
        key=lambda x: x[0] == settings.MODELTRANSLATION_DEFAULT_LANGUAGE,
        reverse=True
    )
    for lang_code, lang_name in languages:
        if lang_code == settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
            form.fields[field_name + "_" + lang_code] = forms.CharField(
                label=default_label.format(lang=lang_code),
                required=require_default
            )
        else:
            form.fields[field_name + "_" + lang_code] = forms.CharField(
                label=alternative_label.format(lang=lang_code),
                required=False
            )
                
# NOTE: not used currently because it introduced new problems
#       leaving this here in case the solution is revisited
def save_translated_field(model_instance, field_name, value):
    """
    Reads a translated charfield and saves it in one of two ways. If it is
    the default language field, it will be saved as is. If it is not the
    default lang, it will still be saved into the default lang attribute
    if it's currently empty.
    """

    lang = translation.get_language()
    default_lang = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
    if lang == default_lang:
        setattr(model_instance, field_name + "_" + lang, value)
    else:
        if not getattr(model_instance, field_name + "_" + default_lang):
            setattr(model_instance, field_name + "_" + default_lang, value)
        else:
            setattr(model_instance, field_name + "_" + lang, value)
        
    
    
class TranslationStaffForm(ModelForm):

    def get_initial_for_field(self, field, field_name):
        if self._instance:
            if field_name in self._translated_field_names:
                return getattr(self._instance, field_name)

        return super().get_initial_for_field(field, field_name)

    def save(self, commit=True):
        instance = super().save(commit=False)
        for lang_field_name in self._translated_field_names:
            setattr(instance, lang_field_name, self.cleaned_data.get(lang_field_name, ""))
        if commit:
            instance.save()
            self.save_m2m()
        else:
            return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._instance = kwargs.get("instance")
        self._translated_field_names = []
        model = self.Meta.model
        translated = translator.get_options_for_model(model).get_field_names()
        languages = sorted(
            settings.LANGUAGES,
            key=lambda x: x[0] == settings.MODELTRANSLATION_DEFAULT_LANGUAGE,
            reverse=True
        )
        for field_name in self.Meta.fields[:]:
            if field_name in translated:
                field = getattr(model, field_name).field
                for lang_code, lang_name in languages:
                    lang_field_name = f"{field_name}_{lang_code}"
                    if lang_code == settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
                        self.fields[lang_field_name] = forms.CharField(
                            label=f"{field.verbose_name} (default)",
                            required=not field.blank
                        )
                    else:
                        self.fields[lang_field_name] = forms.CharField(
                            label=f"{field.verbose_name} ({lang_code})",
                            required=False
                        )
                    if isinstance(field, models.TextField):
                        self.fields[lang_field_name].widget = forms.Textarea(
                            attrs={"class": "generic-textfield", "rows": 5}
                        )
                    self._translated_field_names.append(lang_field_name)
                self.fields.pop(field_name)










