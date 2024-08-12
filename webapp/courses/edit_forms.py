from collections import defaultdict
import os.path
import re
import pygments
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django import forms
from django.forms import fields
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from modeltranslation.forms import TranslationModelForm
from utils.archive import find_latest_version
from utils.formatters import display_name
from utils.management import (
    add_translated_charfields,
    CourseContentAdmin,
    CourseMediaAdmin,
    TranslationStaffForm,
)
from courses import blockparser
from courses import markupparser
import courses.models as cm


def parse_line(line, markup_cls, context):
    pat = re.compile(markup_cls.regexp)
    match_obj = pat.match(line)
    return match_obj.groupdict(default="")


def get_form(block_type, position, context, action, form_post=None, form_files=None):
    if action == "delete":
        form_class = LineDeleteForm
    elif action == "include":
        form_class = markupparser.MarkupParser.include_forms[block_type]
    else:
        form_class = markupparser.MarkupParser.edit_forms[block_type]

    lines = context["content"].content.splitlines()
    revision=find_latest_version(context["content"]).revision_id
    lines = lines[position["line_idx"]:position["line_idx"] + position["line_count"]]

    if form_post is None:
        form = form_class(
            new=action in ("include", "add"),
            lines=lines, context=context, revision=revision,
            **position
        )
    else:
        form = form_class(
            form_post, form_files,
            new=action in ("include", "add"),
            lines=lines, context=context,
            revision=revision,
            **position
        )
    return form


def save_form(form, commit=True):
    if hasattr(form, "save"):
        if not form.cleaned_data.get("delete"):
            return form.save(commit)
    return None


def place_into_content(content, form):
    if form.cleaned_data.get("delete"):
        content.replace_lines(
            form.cleaned_data["line_idx"],
            "",
            delete_count=form.cleaned_data["line_count"]
        )
    else:
        placement = form.cleaned_data["placement"]
        if placement == "after":
            content.replace_lines(
                form.cleaned_data["line_idx"] + form.cleaned_data["line_count"],
                [""] + form.generate_new_markup(),
                delete_count=0
            )
        elif placement == "before":
            content.replace_lines(
                form.cleaned_data["line_idx"],
                form.generate_new_markup() + [""],
                delete_count=0
            )
        else:
            content.replace_lines(
                form.cleaned_data["line_idx"],
                form.generate_new_markup(),
                delete_count=form.cleaned_data["line_count"]
            )

    if getattr(form, "reference_changed", False):
        for instance in cm.CourseInstance.objects.filter(
            Q(contentgraph__content=content)
            | Q(contentgraph__content__embedded_pages=content),
            frozen=False,
        ).distinct():
            content.update_embedded_links(instance)


class LineEditMixin:

    _name = ""

    def clean_opened_revision(self):
        data = self.cleaned_data["opened_revision"]
        if data != self._current_revision:
            raise ValidationError(
                _("Content has been changed after form was opened. Please re-open the form")
            )

    def __init__(self, *args, **kwargs):
        line_idx = kwargs.pop("line_idx", 0)
        line_count = kwargs.pop("line_count", 1)
        placement = kwargs.pop("placement")
        self._current_revision = kwargs.pop("revision")
        super().__init__(*args, **kwargs)
        self.fields["line_idx"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=line_idx
        )
        self.fields["line_count"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=line_count
        )
        self.fields["opened_revision"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=self._current_revision
        )
        self.fields["block_type"] = forms.CharField(
            widget=forms.HiddenInput,
            initial=self._name,
        )
        self.fields["placement"] = forms.ChoiceField(
            widget=forms.HiddenInput,
            initial=placement,
            choices=(
                ("replace", "replace"),
                ("before", "before"),
                ("after", "after"),
            ),
        )

    def generate_new_markup(self):
        return self._markup.markup_from_dict(self.cleaned_data).split("\n")


class LineDeleteForm(LineEditMixin, forms.Form):

    _name = "any"
    @property
    def reference_changed(self):
        return True

    def __init__(self, *args, **kwargs):
        __ = kwargs.pop("context")
        __ = kwargs.pop("lines")
        __ = kwargs.pop("new")
        super().__init__(*args, **kwargs)
        self.fields["delete"] = forms.BooleanField(required=True, label=_("Delete block"))


class EmbeddedObjectEditForm(TranslationStaffForm):

    class Meta:
        model = None
        fields = []
        ref_field = ""
        markup = None

    def get_initial_for_field(self, field, field_name):
        try:
            return self._settings[field_name]
        except KeyError:
            return super().get_initial_for_field(field, field_name)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.name = self.cleaned_data[self.Meta.ref_field]
        if commit:
            instance = super().save(commit=False)
            instance.origin = self._context["course"]
            instance.save()
            return self.save_m2m()
        return instance

    @property
    def reference_changed(self):
        return not self._settings

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        lines = kwargs.pop("lines")
        new = kwargs.pop("new")
        self._settings = {}
        self._markup = self.Meta.markup
        if not new:
            line = lines[0]
            self._settings.update(parse_line(line, self._markup, self._context))
            instance = self.Meta.model.objects.get(name=self._settings[self.Meta.ref_field])
            kwargs["instance"] = instance
        super().__init__(*args, **kwargs)
        if new:
            self.fields[self.Meta.ref_field] = forms.CharField(
                label=_("Name for new object"),
                required=True
            )
        else:
            self.fields[self.Meta.ref_field] = forms.CharField(
                disabled=True,
                initial=self._settings[self.Meta.ref_field],
            )


class EmbeddedObjectIncludeForm(forms.Form):

    class Meta:
        ref_field = ""
        markup = None

    @property
    def reference_changed(self):
        return True

    def _get_instance(self):
        raise NotImplementedError

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        self._markup = self.Meta.markup
        lines = kwargs.pop("lines")
        new = kwargs.pop("new")
        super().__init__(*args, **kwargs)
        self.fields[self.Meta.ref_field] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose existing object"),
            choices=self.get_choices(),
            required=True,
        )

    def get_choices(self):
        return []


class MarkupEditForm(forms.Form):

    def get_initial_for_field(self, field, field_name):
        try:
            return self._settings[field_name]
        except KeyError:
            return super().get_initial_for_field(field, field_name)

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        self._lines = kwargs.pop("lines")
        self._new = kwargs.pop("new")
        self._settings = {}
        if not self._new:
            self._settings.update(parse_line(self._lines[0], self._markup, self._context))
        super().__init__(*args, **kwargs)



class CodeEditForm(LineEditMixin, MarkupEditForm):

    _name = "code"
    _markup = markupparser.CodeMarkup
    highlight = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("Code block content"),
            required=True,
            initial="\n".join(self._lines[1:-1]) if not self._new else "",
        )


class HeadingEditForm(LineEditMixin, MarkupEditForm):

    _name = "heading"
    _markup = markupparser.HeadingMarkup
    level = forms.IntegerField(required=True)

    def get_initial_for_field(self, field, field_name):
        if field_name == "level":
            try:
                return len(self._settings["level"])
            except KeyError:
                pass
        return super().get_initial_for_field(field, field_name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            label=_("Heading text"),
            required=True,
            initial=self._lines[0].strip("= ") if not self._new else "",
        )




class ListEditForm(LineEditMixin, MarkupEditForm):

    _name = "list"
    _markup = markupparser.ListMarkup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("List markup"),
            required=True,
            initial="\n".join(self._lines) if not self._new else "",
        )


class ParagraphEditForm(LineEditMixin, MarkupEditForm):

    _name = "paragraph"
    _markup = markupparser.ParagraphMarkup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("Paragraph markup"),
            required=True,
            initial="\n".join(self._lines) if not self._new else "",
        )


class SeparatorEditForm(LineEditMixin, MarkupEditForm):

    _name = "separator"
    _markup = markupparser.SeparatorMarkup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SvgEditForm(LineEditMixin, MarkupEditForm):

    _name = "svg"
    _markup = markupparser.SvgMarkup
    svg_width = forms.IntegerField(required=True)
    svg_height = forms.IntegerField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("SVG markup"),
            required=True,
            initial="\n".join(self._lines[1:-1]) if not self._new else "",
        )


class TableEditForm(LineEditMixin, MarkupEditForm):

    _name = "table"
    _markup = markupparser.TableMarkup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("Table markup"),
            required=True,
            initial="\n".join(self._lines) if not self._new else "",
        )


class TeXEditForm(LineEditMixin, MarkupEditForm):

    _name = "tex"
    _markup = markupparser.TeXMarkup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("KaTeX markup"),
            required=True,
            initial="\n".join(self._lines[1:-1]) if not self._new else "",
        )


class ScriptFileInline(TranslationStaffForm):

    class Meta:
        model = cm.File
        fields = ["fileinfo", "name"]
        ref_field = "name"

    name = forms.CharField(
        required=False,
    )

    def clean(self):
        default_lang = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
        self._save_ok = False
        cleaned_data = super().clean()
        self._save_ok = True
        if not cleaned_data["existing"]:
            if not cleaned_data[f"fileinfo_{default_lang}"] and not cleaned_data["name"]:
                self._save_ok = False
                self.add_error(
                    "existing", _("This field or name and fileinfo must be filled")
                )
            else:
                if not cleaned_data[f"fileinfo_{default_lang}"]:
                    self._save_ok = False
                    self.add_error(
                        f"fileinfo_{default_lang}", _("This field cannot be empty for new files")
                    )
                if not cleaned_data["name"]:
                    self._save_ok = False
                    self.add_error(
                        "name", _("This field cannot be empty for new files")
                    )

    def save(self, commit=True):
        if self._save_ok:
            if not self.cleaned_data["existing"]:
                instance = super().save(commit=False)
                instance.origin = self._context["course"]
                instance.save()

        return None

    def _parse_include(self, include):
        try:
            where, rest = include.split(":")
            itype, slug = rest.split("=")
        except:
            return "", "", ""
        return slug, itype, where

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context", None)
        self.prefix = kwargs["prefix"]
        accessible_files = kwargs.pop("accessible_files")
        slug, itype, where = self._parse_include(kwargs.pop("include", ""))
        instance = cm.File.objects.filter(name=slug).first()
        kwargs["instance"] = instance
        super().__init__(*args, requires=False, **kwargs)
        self.fields["existing"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose existing include"),
            choices=[("", _("----NOT--SELECTED----"))] + accessible_files,
            required=False,
            initial=instance and instance.name,
        )
        self.fields["type"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Include type"),
            choices=[("script", "script"), ("style", "style"), ("image", "image")],
            required=True,
            initial=itype,
        )
        self.fields["where"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("DOM location"),
            choices=[("head", "head"), ("body", "body")],
            required=True,
            initial=where,
        )
        self.fields["delete"] = forms.BooleanField(
            label=_("Unlink"),
            required=False,
        )
        if instance:
            self.fields["name"].disabled = True
            self.fields["existing"].disabled = True
            self.fields["type"].disabled = True
            self.fields["where"].disabled = True


class ScriptEditForm(LineEditMixin, EmbeddedObjectEditForm):

    _name = "script"
    _markup = markupparser.EmbeddedScriptMarkup
    has_inline = True

    class Meta:
        model = cm.File
        fields = ["fileinfo"]
        ref_field = "script_slug"
        markup = markupparser.EmbeddedScriptMarkup

    def get_initial_for_field(self, field, field_name):
        try:
            return self._settings[field_name]
        except KeyError:
            return super().get_initial_for_field(field, field_name)

    def is_valid(self):
        if super().is_valid():
            for inline in self._include_formset:
                if not inline.is_valid():
                    for field, error in inline.errors.items():
                        self.errors[f"{inline.prefix}-{field}"] = error
                    return False
                for key, value in inline.cleaned_data.items():
                    self.cleaned_data[f"{inline.prefix}-{key}"] = value
            return True

        return False

    def clean(self):
        default_lang = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
        cleaned_data = super().clean()
        if not cleaned_data["existing"]:
            if not cleaned_data[f"fileinfo_{default_lang}"] or not cleaned_data[self.Meta.ref_field]:
                raise ValidationError(_(
                    "Existing file must be chosen, or both fileinfo and "
                    "name must be filled to create a new file"
                ))

    def save(self, commit=True):
        if self.cleaned_data["existing"]:
            self.cleaned_data["script_slug"] = self.cleaned_data["existing"]
        else:
            instance = super().save(commit=False)
            instance.origin = self._context["course"]
            instance.save()
        for inline in self._include_formset:
            inline.save(commit)

    @property
    def reference_changed(self):
        return True

    def get_inline_formset(self):
        return self._include_formset

    def inline_header(self):
        return _("Included files")

    def empty_form(self):
        return ScriptFileInline(
            prefix=f"include_files-__prefix__",
            accessible_files=self._accessible_files,
            context=self._context
        )

    def get_choices(self):
        return  [(f.name, f.name)
            for f in CourseMediaAdmin.media_access_list(
                self._context["request"], cm.File
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, requires=False, **kwargs)
        self.fields["script_width"] = forms.IntegerField(label=_("iframe width"), required=True)
        self.fields["script_height"] = forms.IntegerField(label=_("iframe height"), required=True)
        self.fields["border"] = forms.CharField(label=_("Border CSS"), required=False)
        included_files_str = self._settings.get("include", "")
        included_files = included_files_str.split(",") if included_files_str else []
        self.fields[self.Meta.ref_field].required = False
        self.fields["include_files-TOTAL_FORMS"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=len(included_files)
        )
        self.fields["include_files-INITIAL_FORMS"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=len(included_files)
        )
        self.fields["include_files-MIN_NUM_FORMS"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=1
        )
        self.fields["include_files-MAX_NUM_FORMS"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=1000
        )
        self._accessible_files = self.get_choices()
        self.fields["existing"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose existing script"),
            choices=[("", _("----NOT--SELECTED----"))] + self._accessible_files,
            required=False,
        )
        self._include_formset = [
            ScriptFileInline(
                getattr(self._context["request"], "POST", None) if self.is_bound else None,
                getattr(self._context["request"], "FILES", None) if self.is_bound else None,
                include=include,
                context=self._context,
                accessible_files=self._accessible_files,
                prefix=f"include_files-{i}",
            ) for i, include in enumerate(included_files)
        ]
        try:
            total_on_form = int(getattr(
                self._context["request"], "POST"
            )["include_files-TOTAL_FORMS"])
        except (AttributeError, KeyError):
            total_on_form = len(included_files)

        for i in range(len(included_files), total_on_form):
            self._include_formset.append(ScriptFileInline(
                getattr(self._context["request"], "POST", None) if self.is_bound else None,
                getattr(self._context["request"], "FILES", None) if self.is_bound else None,
                context=self._context,
                accessible_files=self._accessible_files,
                prefix=f"include_files-{i}",)
            )


class ImageEditForm(LineEditMixin, EmbeddedObjectEditForm):

    _name = "image"

    class Meta:
        model = cm.Image
        fields = ["description", "fileinfo"]
        ref_field = "image_name"
        markup = markupparser.ImageMarkup

    alt_text = forms.CharField(required=False)
    caption_text = forms.CharField(required=False)
    align = forms.CharField(required=False)


class ImageIncludeForm(LineEditMixin, EmbeddedObjectIncludeForm):

    _name = "image"

    class Meta:
        ref_field = "image_name"
        markup = markupparser.ImageMarkup

    def get_choices(self):
        return sorted(((image.name, image.name)
            for image in CourseMediaAdmin.media_access_list(
                self._context["request"], cm.Image
            )
        ))


class FileEditForm(LineEditMixin, EmbeddedObjectEditForm):

    _name = "file"

    class Meta:
        model = cm.File
        fields = ["typeinfo", "fileinfo", "download_as"]
        ref_field = "file_slug"
        markup = markupparser.EmbeddedFileMarkup


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["link_only"] = forms.BooleanField(label=_("No content preview"), required=False)


class FileIncludeForm(LineEditMixin, EmbeddedObjectIncludeForm):

    _name = "file"

    class Meta:
        ref_field = "file_slug"
        markup = markupparser.EmbeddedFileMarkup

    def get_choices(self):
        return sorted(((f.name, f.name)
            for f in CourseMediaAdmin.media_access_list(
                self._context["request"], cm.File
            )
        ))


class VideoEditForm(LineEditMixin, EmbeddedObjectEditForm):

    _name = "video"

    class Meta:
        model = cm.VideoLink
        fields = ["description", "link"]
        ref_field = "video_slug"
        markup = markupparser.EmbeddedVideoMarkup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["video_width"] = forms.IntegerField(label=_("iframe width"), required=True)
        self.fields["video_height"] = forms.IntegerField(label=_("iframe height"), required=True)


class VideoIncludeForm(LineEditMixin, EmbeddedObjectIncludeForm):

    _name = "video"

    class Meta:
        ref_field = "video_slug"
        markup = markupparser.EmbeddedVideoMarkup

    def get_choices(self):
        return sorted(((video.name, video.name)
            for video in CourseMediaAdmin.media_access_list(
                self._context["request"], cm.VideoLink
            )
        ))


class TaskCreateForm(LineEditMixin, TranslationStaffForm):

    _name = "embedded_page"

    class Meta:
        model = cm.ContentPage
        fields = ["name"]
        markup = markupparser.EmbeddedPageMarkup

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.content_type = self.cleaned_data["content_type"]
        instance.origin = self._context["course"]
        instance.save()
        self.cleaned_data["page_slug"] = instance.slug

    @property
    def reference_changed(self):
        return True

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        self._markup = self.Meta.markup
        kwargs.pop("lines")
        kwargs.pop("new")
        super().__init__(*args, **kwargs)
        self.fields["content_type"] = forms.ChoiceField(
            widget=forms.Select,
            choices=(
                choice for choice in cm.ContentPage.CONTENT_TYPE_CHOICES if choice[0] != "LECTURE"
            )
        )



class TaskIncludeForm(LineEditMixin, EmbeddedObjectIncludeForm):

    _name = "embedded_page"

    class Meta:
        ref_field = "page_slug"
        markup = markupparser.EmbeddedPageMarkup

    def get_choices(self):
        return sorted(((page.slug, page.name)
            for page in CourseContentAdmin.content_access_list(
                self._context["request"], cm.ContentPage
            ) if page.content_type != "LECTURE"
        ))


class CalendarCreateForm(LineEditMixin, forms.ModelForm):

    _name = "calendar"

    class Meta:
        model = cm.Calendar
        fields = ["name", "allow_multiple"]
        markup = markupparser.CalendarMarkup

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.save()
        self.cleaned_data["calendar_name"] = instance.name

    @property
    def reference_changed(self):
        return True

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        self._markup = self.Meta.markup
        kwargs.pop("lines")
        kwargs.pop("new")
        super().__init__(*args, **kwargs)


class BlockTypeSelectForm(forms.Form):

    def __init__(self, *args, **kwargs):
        line_idx = kwargs.pop("line_idx", 0)
        line_count = kwargs.pop("line_count", 0)
        super().__init__(*args, **kwargs)
        self.fields["placement"] = forms.ChoiceField(
            widget=forms.RadioSelect,
            label=_("Placement"),
            required=True,
            choices=(
                ("before", _("Before highlighted content block")),
                ("after", _("After highlighted content block")),
            ),
            initial="after",
        )
        self.fields["mode"] = forms.ChoiceField(
            widget=forms.RadioSelect,
            label=_("Mode (if applicable)"),
            required=False,
            choices=(
                ("create", _("Create a new object")),
                ("include", _("Include an existing object")),
            ),
            initial="create",
        )
        self.fields["line_idx"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=line_idx
        )
        self.fields["line_count"] = forms.IntegerField(
            widget=forms.HiddenInput,
            initial=line_count
        )
        self.fields["block_type"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Block type to add"),
            choices=[
                (markup, markup.replace("_", " ").capitalize())
                for markup in markupparser.MarkupParser.editable_markups()
            ],
            required=True
        )


class TermifyForm(forms.Form):


    def __init__(self, *args, **kwargs):
        terms = kwargs.pop("course_terms")
        super().__init__(*args, **kwargs)
        self.fields["baseword"] = forms.CharField(label=_("Base word"), required=True)
        self.fields["inflections"] = forms.CharField(
            label=_("Inflections (comma sep.)"),
            required=False
        )
        self.fields["replace_in"] = forms.MultipleChoiceField(
            widget=forms.CheckboxSelectMultiple,
            label=_("Replace in"),
            choices=[
                ("list", "List"),
                ("paragraph", "Paragraph"),
                ("table", "Table"),
            ],
            required=False
        )
        self.fields["term"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Term"),
            choices=[(term.name, term.name) for term in terms]
        )





markupparser.MarkupParser.register_form("calendar", "edit", CalendarCreateForm)
markupparser.MarkupParser.register_form("code", "edit", CodeEditForm)
markupparser.MarkupParser.register_form("embedded_page", "edit", TaskCreateForm)
markupparser.MarkupParser.register_form("embedded_page", "include", TaskIncludeForm)
markupparser.MarkupParser.register_form("file", "edit", FileEditForm)
markupparser.MarkupParser.register_form("file", "include", FileIncludeForm)
markupparser.MarkupParser.register_form("heading", "edit", HeadingEditForm)
markupparser.MarkupParser.register_form("image", "edit", ImageEditForm)
markupparser.MarkupParser.register_form("image", "include", ImageIncludeForm)
markupparser.MarkupParser.register_form("list", "edit", ListEditForm)
markupparser.MarkupParser.register_form("paragraph", "edit", ParagraphEditForm)
markupparser.MarkupParser.register_form("separator", "edit", SeparatorEditForm)
markupparser.MarkupParser.register_form("script", "edit", ScriptEditForm)
markupparser.MarkupParser.register_form("svg", "edit", SvgEditForm)
markupparser.MarkupParser.register_form("table", "edit", TableEditForm)
markupparser.MarkupParser.register_form("tex", "edit", TeXEditForm)
markupparser.MarkupParser.register_form("video", "edit", VideoEditForm)
markupparser.MarkupParser.register_form("video", "include", VideoIncludeForm)





