from django.http import (
    HttpResponse,
)
from django.shortcuts import render
from django.template import loader
from courses.widgets import PreviewWidgetRegistry

# Create your views here.

def get_widget_subform(request, instance, content):
    widget = request.GET.get("value")
    try:
        preview_widget = PreviewWidgetRegistry.get_widget(
            widget, instance, content
        )
    except KeyError:
        print(widget)
        return HttpResponse("")

    form = preview_widget.get_configuration_form(prefix="extra")
    form_t = loader.get_template("courses/edit-form-inline.html")
    form_c = {"form": form}
    return HttpResponse(form_t.render(form_c, request))

