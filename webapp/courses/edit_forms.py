import os.path
import re
import pygments
import django.conf
from django.core.exceptions import ValidationError
from django.db.models import Count
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
    if action == "include":
        forms = {
            "file": FileIncludeForm,
            "image": ImageIncludeForm,
        }
    else:
        forms = {
            "code": CodeEditForm,
            "file": FileEditForm,
            "image": ImageEditForm,
        }

    lines = context["content"].content.splitlines()
    revision=find_latest_version(context["content"]).revision_id
    lines = lines[position["line_idx"]:position["line_idx"] + position["line_count"]]

    if form_post is None:
        form = forms[block_type](
            new=action!="edit",
            lines=lines, context=context, revision=revision,
            **position
        )
    else:
        form = forms[block_type](
            form_post, form_files,
            new=action!="edit",
            lines=lines, context=context,
            revision=revision,
            **position
        )
    return form


def save_form(form, commit=True):
    if hasattr(form, "save"):
        return form.save(commit)
    return None


def place_into_content(content, form):
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



class LineEditMixin:

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


class CodeEditForm(LineEditMixin, forms.Form):

    block_type = forms.CharField(
        widget=forms.HiddenInput,
        initial="code"
    )

    highlight = forms.CharField(required=False)

    def get_initial_for_field(self, field, field_name):
        try:
            return self._settings[field_name]
        except KeyError:
            return super().get_initial_for_field(field, field_name)

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        lines = kwargs.pop("lines")
        new = kwargs.pop("new")
        self._settings = {}
        self._markup = markupparser.CodeMarkup
        if not new:
            self._settings.update(parse_line(lines[0], self._markup, self._context))
        super().__init__(*args, **kwargs)
        self.fields["content"] = forms.CharField(
            widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
            label=_("Code block content"),
            required=True,
            initial="\n".join(lines[1:-1]),
        )


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
            instance.save()
            return self.save_m2m()
        return instance

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        line = kwargs.pop("lines")[0]
        new = kwargs.pop("new")
        self._settings = {}
        self._markup = self.Meta.markup
        if not new:
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

    def __init__(self, *args, **kwargs):
        self._context = kwargs.pop("context")
        self._markup = self.Meta.markup
        lines = kwargs.pop("lines")[0]
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


class ImageEditForm(LineEditMixin, EmbeddedObjectEditForm):

    class Meta:
        model = cm.Image
        fields = ["description", "fileinfo"]
        ref_field = "image_name"
        markup = markupparser.ImageMarkup


    block_type = forms.CharField(
        widget=forms.HiddenInput,
        initial="image"
    )

    alt_text = forms.CharField(required=False)
    caption_text = forms.CharField(required=False)
    align = forms.CharField(required=False)


class ImageIncludeForm(LineEditMixin, EmbeddedObjectIncludeForm):

    class Meta:
        ref_field = "image_name"
        markup = markupparser.ImageMarkup

    block_type = forms.CharField(
        widget=forms.HiddenInput,
        initial="image"
    )

    def get_choices(self):
        return ((image.name, image.name)
            for image in CourseMediaAdmin.media_access_list(
                self._context["request"], cm.Image
            )
        )


class FileEditForm(LineEditMixin, EmbeddedObjectEditForm):

    class Meta:
        model = cm.File
        fields = ["typeinfo", "fileinfo", "download_as"]
        ref_field = "file_slug"
        markup = markupparser.EmbeddedFileMarkup

    block_type = forms.CharField(
        widget=forms.HiddenInput,
        initial="file"
    )

    link_only = forms.BooleanField(label=_("No content preview"))


class FileIncludeForm(LineEditMixin, EmbeddedObjectIncludeForm):

    class Meta:
        ref_field = "file_slug"
        markup = markupparser.EmbeddedFileMarkup

    block_type = forms.CharField(
        widget=forms.HiddenInput,
        initial="file"
    )

    def get_choices(self):
        return ((f.name, f.name)
            for f in CourseMediaAdmin.media_access_list(
                self._context["request"], cm.File
            )
        )


class BlockTypeSelectForm(forms.Form):

    placement = forms.ChoiceField(
        widget=forms.RadioSelect,
        label=_("Placement"),
        required=True,
        choices=(
            ("before", _("Before highlighted content block")),
            ("after", _("After highlighted content block")),
        ),
        initial="after",
    )
    mode = forms.ChoiceField(
        widget=forms.RadioSelect,
        label=_("Mode (if applicable)"),
        required=False,
        choices=(
            ("create", _("Create a new object")),
            ("include", _("Include an existing object")),
        ),
        initial="create",
    )


    def __init__(self, *args, **kwargs):
        line_idx = kwargs.pop("line_idx", 0)
        line_count = kwargs.pop("line_count", 0)
        super().__init__(*args, **kwargs)
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
                (markup, markup.capitalize())
                for markup in markupparser.MarkupParser.editable_markups()
            ],
            required=True
        )







