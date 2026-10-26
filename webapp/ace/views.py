import os.path
import uuid
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.template import loader
from django.utils import translation

from reversion import revisions as reversion

import courses.models as cm
from courses.widgets import PreviewWidgetRegistry
from utils.access import ensure_staff
from utils.content import regenerate_nearest_cache

from ace.forms import BaseFileSaveConfirmForm
from ace.models import AceWidgetSettings, AcePlusLink

# Create your views here.

def get_widget_subform(request, course, slug):
    if slug == "-default-":
        slug = ""
    widget = request.GET.get("value")
    try:
        preview_widget = PreviewWidgetRegistry.get_widget(
            widget, course, slug
        )
    except KeyError:
        return HttpResponse("")

    form = preview_widget.get_configuration_form(request, prefix="extra")
    form_t = loader.get_template("courses/edit-form-inline.html")
    form_c = {"form": form}
    return HttpResponse(form_t.render(form_c, request))

@ensure_staff
def save_base_file(request, course, instance, slug):

    widget = AceWidgetSettings.objects.get(slug=slug)
    current_lang = translation.get_language()
    lang_field = f"fileinfo_{current_lang}"
    lang_file_exists = True
    if current_lang != settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
        if not getattr(widget.base_file, lang_field):
            lang_file_exists = False

    if request.method == "POST":
        form = BaseFileSaveConfirmForm(
            request.POST, widget_slug=slug, lang_file_exists=lang_file_exists
        )
        if not form.is_valid():
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        if not lang_file_exists:
            if form.cleaned_data["write_to"] == "default":
                current_lang = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
                lang_field = f"fileinfo_{settings.MODELTRANSLATION_DEFAULT_LANGUAGE}"

        widget = AceWidgetSettings.objects.get(slug=slug)
        file_obj = ContentFile(
            bytes(form.cleaned_data["editor_content"].replace("\r", ""), encoding="utf-8")
        )
        if form.cleaned_data["filename"]:
            filename = form.cleaned_data["filename"]
            setattr(widget.base_file, f"download_as_{current_lang}", filename)
        else:
            filename = f"base-file-{uuid.uuid1()}"

        with reversion.create_revision():
            getattr(widget.base_file, lang_field).save(filename, file_obj)
            widget.base_file.save()
            reversion.set_user(request.user)
            reversion.set_comment(f"Updated base file ({lang_field}) content")

        for link in AcePlusLink.objects.filter(widget_slug=slug):
            link.parent.regenerate_cache(link.instance, active_only=True)
        for page in cm.ContentPage.objects.filter(slug=slug):
            regenerate_nearest_cache(page)

        return JsonResponse({"status": "ok"})

    form = BaseFileSaveConfirmForm(
        widget_slug=slug,
        lang_file_exists=lang_file_exists,
        initial={
            "filename": getattr(widget.base_file, f"download_as_{current_lang}")
        }
    )
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "html_id": f"{slug}-base-file-form",
        "html_class": "edit-form-widget",
        "submit_url": request.path,
        "submit_override": "acewidget.save_base_file"
    }
    return HttpResponse(form_t.render(form_c, request))

