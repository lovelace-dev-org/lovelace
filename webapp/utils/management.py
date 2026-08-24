from django.conf import settings
from django.contrib import admin
from django.db.models import Q
from django.db import models, transaction
from django import forms
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.forms import Textarea, ModelForm
from django.template import loader
from django.utils.translation import gettext_lazy as _

from django.utils import translation
from django.utils.text import slugify

from reversion import revisions as reversion
from reversion.models import Version

from modeltranslation.translator import translator
import courses.models as cm
from courses.widgets import ContentPreviewWidget, AdminFileWidget
from utils.access import determine_access, determine_media_access
from utils.archive import find_latest_version, squash_revisions
from utils.content import regenerate_nearest_cache
from utils.data import serialize_single_python, export_json


# TODO: There's a loophole where staff members of any course A can gain access
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
    def content_access_list(request, model, content_type=None, origin=None):
        """
        Gets a queryset of content where the requesting user either:
        1) has edited the page previously
        2) belongs to the staff of a course that contains the content
           either as a contentgraph node or as an embedded page

        The content type is read from the content_type attribute. Child
        classes should set this attribute to control which type of
        content is shown.
        """

        if origin is None:
            if content_type:
                qs = model.objects.filter(content_type=content_type)
            else:
                qs = model.objects.all()
        else:
            if content_type:
                qs = model.objects.filter(content_type=content_type, origin=origin)
            else:
                qs = model.objects.filter(origin=origin)

        if request.user.is_superuser:
            return qs

        edited = (
            Version.objects.get_for_model(model)
            .filter(revision__user=request.user)
            .values_list("object_id", flat=True)
        )

        qs = qs.filter(
            Q(id__in=list(edited))
            | Q(contentgraph__instance__course__staff_group__user=request.user)
            | Q(
                emb_embedded__parent__contentgraph__instance__course__staff_group__user=request.user
            )
            | Q(contentgraph__instance__course__main_responsible=request.user)
            | Q(
                emb_embedded__parent__contentgraph__instance__course__main_responsible=request.user
            )
        ).distinct()

        return qs

    def get_queryset(self, request):
        return CourseContentAdmin.content_access_list(request, self.model, self.content_type).defer(
            "content"
        )

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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """
        Sets widgets for content and tags fields. Content in particular gets
        the preview widget which is capable of showing a rendered preview
        without saving the content first.
        """

        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ("content"):
            formfield.widget = ContentPreviewWidget(attrs={"rows": 25, "cols": 120})
        elif db_field.name == "tags":
            formfield.widget = Textarea(attrs={"rows": 2})
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

        parents = cm.ContentPage.objects.filter(embedded_pages=self.current).distinct()
        for instance in cm.CourseInstance.objects.filter(
            Q(contentgraph__content=self.current)
            | Q(contentgraph__content__embedded_pages=self.current),
            frozen=False,
        ).distinct():
            self.current.update_embedded_links(instance)
            if self.current.content_type == "LECTURE":
                self.current.regenerate_cache(instance)
            for parent in parents:
                parent.regenerate_cache(instance)
            instance.clear_content_tree_cache()

    def _find_contexts(self, obj):
        """
        Find the context(s) (course instances) where this page is linked that
        have not been frozen.
        """

        instances = cm.CourseInstance.objects.filter(contents__content=obj, contents__revision=None)
        contexts = []
        for instance in instances:
            context = {
                "course": instance.course,
                "course_slug": instance.course.slug,
                "instance": instance,
                "instance_slug": instance.slug,
            }
            contexts.append(context)

        return contexts

    def _match_groups(self, user, obj):
        """
        Matches a user's groups to the staff groups of the target object.
        Returns True if the user is in the staff group of the course that
        is at the end of the access chain for the object.
        """

        if cm.Course.objects.filter(
            Q(courseinstance__contents__content=obj)
            | Q(courseinstance__contents__content__embedded_pages=obj)
        ).filter(staff_group__user=user):
            return True

        return False


class CourseMediaAdmin(admin.ModelAdmin):
    @staticmethod
    def media_access_list(request, model, origin=None):
        if origin is None:
            qs = model.objects.all()
        else:
            qs = model.objects.filter(origin=origin)

        if request.user.is_superuser:
            return qs

        edited = (
            Version.objects.get_for_model(model)
            .filter(revision__user=request.user)
            .values_list("object_id", flat=True)
        )

        user_groups = request.user.groups.get_queryset()

        return qs.filter(
            Q(id__in=list(edited))
            | Q(coursemedialink__instance__course__staff_group__in=user_groups)
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
        if (
            obj.coursemedialink_set.get_queryset()
            .filter(instance__course__staff_group__in=user_groups)
            .distinct()
        ):
            return True

        return False


def clone_instance_files(old_instance, new_instance):
    """
    Creates cloned links to all instance files in a course instance.
    """

    if_links = cm.InstanceIncludeFileToInstanceLink.objects.filter(instance=old_instance)
    for link in if_links:
        link.pk = None
        link.instance = new_instance
        link.save()


def clone_terms(old_instance, new_instance):
    """
    Creates cloned links to all terms in a course instance.
    """

    term_links = cm.TermToInstanceLink.objects.filter(instance=old_instance)
    for link in term_links:
        link.pk = None
        link.instance = new_instance
        link.save()


def clone_grades(old_instance, new_instance):
    """
    Clones grade thresholds when creating a new course instance by cloning.
    """

    grades = cm.GradeThreshold.objects.filter(instance=old_instance)
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

    content_graphs = cm.ContentGraph.objects.filter(instance=old_instance)
    for graph in content_graphs:
        graph.pk = None
        graph.instance = new_instance
        graph.save()
        graph.content.update_embedded_links(new_instance, graph.revision)

    for child_node in cm.ContentGraph.objects.filter(instance=new_instance).exclude(
        parentnode=None
    ):
        new_parent = cm.ContentGraph.objects.get(
            content=child_node.parentnode.content, instance=new_instance
        )
        child_node.parentnode = new_parent
        child_node.save()


def clone_embed_links(old_instance, new_instance):

    embed_links = cm.EmbeddedLink.objects.filter(instance=old_instance)
    for link in embed_links:
        link.pk = None
        link.instance = new_instance
        link.save()


def freeze_context_link(link_object, revisioned_attr, freeze_to=None):
    """
    Utility function to freeze a context link (e.g. ContentGraph) by setting its revision
    attribute to either the latest revision, or the revision specified by the freeze_to
    parameter.
    """

    if getattr(link_object, "evergreen", False):
        return

    try:
        version = find_latest_version(getattr(link_object, revisioned_attr), freeze_to)
    except Version.DoesNotExist:
        link_object.delete()
        return

    link_object.revision = version.revision_id
    link_object.save()


def add_translated_charfields(
    form, field_name, default_label, alternative_label, require_default=True
):
    """
    Adds charfields to a form for all languages. Used in generating many admin
    forms. Will treat MODELTRANSLATION_DEFAULT_LANGUAGE as the primary language
    and other languages as secondary that are always optional. The primary can
    be set to optional for fields that are optional. Labels need to be given
    separately for the default field, and for alternative fields.

    Deprecated, use TranslationStaffForm instead.
    """

    languages = sorted(
        settings.LANGUAGES,
        key=lambda x: x[0] == settings.MODELTRANSLATION_DEFAULT_LANGUAGE,
        reverse=True,
    )
    for lang_code, __ in languages:
        if lang_code == settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
            form.fields[field_name + "_" + lang_code] = forms.CharField(
                label=default_label.format(lang=lang_code), required=require_default
            )
        else:
            form.fields[field_name + "_" + lang_code] = forms.CharField(
                label=alternative_label.format(lang=lang_code), required=False
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
    """
    Utility form parent class that makes it easier to work with translated fields. If using
    modeltranslation's own traslation form, it will always save to the active language which can
    lead to all sorts of havoc. This form class instead displays the value in every language for
    a translated field so that they can be edited similarly to the admin interface. It also labels
    the default language clearly, and makes it mandatory if the field itself is mandatory.

    Always use this class as a form class' parent if it is intended to be able to edit values in all
    languages.
    """

    def get_initial_for_field(self, field, field_name):
        if self._instance:
            if field_name in self._translated_field_names:
                return getattr(self._instance, field_name)

        return super().get_initial_for_field(field, field_name)

    def save(self, commit=True):
        # TODO: After updating Django check if this still needed
        #       seems like an unnecessary hack?
        for field_name, field in self.fields.items():
            if isinstance(field, forms.FileField):
                if self.cleaned_data[field_name] is False:
                    self.cleaned_data[field_name] = None

        instance = super().save(commit=False)
        for lang_field_name in self._translated_field_names:
            setattr(instance, lang_field_name, self.cleaned_data.get(lang_field_name, ""))
        if commit:
            instance.save()
            return self.save_m2m()
        return instance

    def visible_fields(self):
        def meta_listing_index(field):
            for i, field_name in enumerate(self.Meta.fields):
                if field.name.startswith(field_name):
                    return i
            return len(self.Meta.fields)

        fields = super().visible_fields()
        fields.sort(key=meta_listing_index)
        return fields

    def field_changed(self, field):
        for lang_code, __ in settings.LANGUAGES:
            # Unset fileinfo is empty string in the model
            current = getattr(self._instance, f"{field}_{lang_code}", "") or None
            if current != self.cleaned_data[f"{field}_{lang_code}"]:
                return True
        return False

    def __init__(self, *args, requires=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._instance = kwargs.get("instance")
        self._translated_field_names = []
        model = self.Meta.model
        translated = translator.get_options_for_model(model).get_field_names()
        languages = sorted(
            settings.LANGUAGES,
            key=lambda x: x[0] == settings.MODELTRANSLATION_DEFAULT_LANGUAGE,
            reverse=True,
        )
        for field_name in self.Meta.fields:
            if field_name in translated:
                field = getattr(model, field_name).field
                for lang_code, __ in languages:
                    lang_field_name = f"{field_name}_{lang_code}"
                    if lang_code == settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
                        required = requires and not field.blank
                        self.fields[lang_field_name] = field.formfield(
                            label=f"{field.verbose_name} (default)".capitalize(),
                            required=required,
                        )
                    else:
                        required = False
                        self.fields[lang_field_name] = field.formfield(
                            label=f"{field.verbose_name} ({lang_code})".capitalize(),
                            required=False
                        )
                    if isinstance(field, models.TextField):
                        self.fields[lang_field_name].widget = forms.Textarea(
                            attrs={"class": "generic-textfield", "rows": 5}
                        )
                    elif isinstance(field, models.FileField):
                        try:
                            widget = self.Meta.widgets[field_name]()
                        except (AttributeError, KeyError):
                            widget = forms.ClearableFileInput()
                        widget.is_required = required
                        self.fields[lang_field_name].widget = widget

                    self._translated_field_names.append(lang_field_name)
                self.fields.pop(field_name)


class ExportImportMixin:

    def natural_key(self):
        """
        Gets the 'natural key' for a model instance. This must be a combination of field
        values that can uniquely identify the model instance and cannot include its database ID.

        Use of natural key must always be paired with the use of a manager that has a get_by_natural
        method.
        """

        raise NotImplementedError

    def export(self, instance, export_target):
        """
        Exports this model instance into a zip file as a json document. Note that this base method
        does not need the instance parameter for anything, but potential overrides might need it.

        :param CourseInstance instance: the course instance being exported
        :param ZipFile export_target: the zip file (or compatible object) export is written to
        """

        document = serialize_single_python(self)
        name = "_".join(self.natural_key())
        export_json(document, name, export_target)


def get_prefixed_slug(model_instance, origin, source_field, translated=True):
    """
    Creates a prefixed slug for the given model instance. This utility function keeps identifiers
    unique within courses, freeing commonly used names for pages etc. to be used in multiple
    courses. Tries to avoid prefixing an already prefixed slug.

    :param Model model_instance: the model instance to attach the slug for
    :param Course origin: the course the model instance originally belongs to
    :param str source_field: name of the field from which slug should be generated from
    :param bool translated: whether the field is managed by modeltranslation or not (default True)

    :return: the prefixed slug as a string
    """

    default_lang = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
    if origin is None:
        prefix = settings.ORPHAN_PREFIX
    else:
        prefix = origin.prefix

    if translated:
        main_slug = slugify(
            getattr(model_instance, f"{source_field}_{default_lang}"),
            allow_unicode=True
        )
    else:
        main_slug = slugify(getattr(model_instance, f"{source_field}"), allow_unicode=True)

    # don't double the prefix if it's already used in the source field (legacy naming habit)
    main_slug = main_slug.removeprefix(f"{prefix}-")

    return f"{prefix}-{main_slug}"


def process_modelform(request, form_cls, model_instance, form_id, comment,
                      parent=None,
                      form_extra=None,
                      post_save_cb=None,
                      extra_context=None,
                      extra_response=None):
    """
    A general utility function for displaying and processing most instances of ModelForms.
    Should be used for most views that are used for displaying and saving a form. Handles
    creating revisions and refreshing cache. Other things can also be controlled with the optional
    parameters.

    :param Request request: request object
    :param ModelForm form_cls: form class, must inherit ModelForm
    :param Model model_instance: model instance being edited, can be None when creating new instance
    :param str form_id: form's HTML id
    :param str comment: comment for the automatically created revision
    :param Model parent: the object's parent when relevant, used in revisioning and cache refresh
    :param function post_save_cb: callback function for additional actions needed when saving the
                                  form, will be given the model instance and the form
    :param dict extra_context: extra/override context that will be updated into the form's rendering
                               context
    :param dict extra_response: extra data that will be updated into the JSON response when
                                saving is successful

    """
    form_extra = form_extra or {}

    if request.method == "POST":
        form = form_cls(request.POST, request.FILES, instance=model_instance, **form_extra)
        if not form.is_valid():
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        with reversion.create_revision():
            if post_save_cb:
                saved_instance = form.save(commit=False)
                post_save_cb(saved_instance, form)
                saved_instance.save()
            else:
                form.save()
            if parent:
                parent.save()
            reversion.set_user(request.user)
            reversion.set_comment(comment)

        if parent:
            squash_revisions(parent, 1)
        elif model_instance:
            squash_revisions(model_instance, 1)

        if getattr(form.Meta, "trigger_cache", False):
            regenerate_nearest_cache(parent or model_instance)

        response = {"status": "ok"}
        extra_response and response.update(extra_response)
        return JsonResponse(response)

    form = form_cls(instance=model_instance, **form_extra)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "html_id": form_id,
        "form_object": form,
        "submit_url": request.path,
        "html_class": "edit-form-widget",
        "submit_override": "editing.submit_form"
    }
    extra_context and form_c.update(extra_context)
    return HttpResponse(form_t.render(form_c, request))


class ConfirmDeleteForm(forms.Form):
    delete = forms.BooleanField(required=True, label=_("Confirm"))



def process_confirm_form(request, success_callback, extra_context=None, extra_response=None):
    """
    Convenience function for displaying and processing a ConfirmDeleteForm. Can be used to reduce
    boilerplate in delete views. The calling end simply needs to define a success callback that
    carries out the deletion once the user has confirmed the operation.

    :param Request request: request object
    :param function success_callback: function that takes a form object as its argument
    :param dict extra_context: extra context data to be added to the form template's rendering
    """

    if request.method == "POST":
        form = ConfirmDeleteForm(request.POST)
        if not form.is_valid():
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        success_callback(form)
        response = {"status": "ok"}
        extra_response and response.update(extra_response)
        return JsonResponse(response)

    form = ConfirmDeleteForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"confirm-form",
        "html_class": "edit-form-widget",
        "submit_label": _("Execute"),
    }
    extra_context and form_c.update(extra_context)
    return HttpResponse(form_t.render(form_c, request))


