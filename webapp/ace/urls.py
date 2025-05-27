from django.urls import path
from . import views

app_name = "ace"

urlpatterns = [
    path(
        "<instance:instance>/<content:content>/preview_settings/",
        views.get_widget_subform,
        name="preview_subform",
    ),
]
