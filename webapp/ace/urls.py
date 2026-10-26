from django.urls import path
from . import views

app_name = "ace"

urlpatterns = [
    path(
        "<course:course>/<str:slug>/preview_settings/",
        views.get_widget_subform,
        name="preview_subform",
    ),
    path(
        "<course:course>/<instance:instance>/<str:slug>/base_file/save/",
        views.save_base_file,
        name="save_base_file"
    )
]
