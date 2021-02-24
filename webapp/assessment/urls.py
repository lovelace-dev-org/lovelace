from django.urls import path
from model_path_converter import register_model_converter
from . import views
from .models import *

app_name = "assessment"

register_model_converter(AssessmentSheet, name="sheet")
register_model_converter(AssessmentBullet, name="bullet")


urlpatterns = [
    path(
        "<course:course>/<instance:instance>/<content:content>/manage/",
        views.manage_assessment,
        name="manage_assessment"
    ),
    path(
        "<course:course>/<instance:instance>/<sheet:sheet>/create_section/",
        views.create_section,
        name="create_section"
    ),
    path(
        "<course:course>/<instance:instance>/<sheet:sheet>/create_bullet/",
        views.create_bullet,
        name="create_bullet"
    ),
    path(
        "<course:course>/<instance:instance>/<sheet:sheet>/rename_section/",
        views.rename_section,
        name="rename_section"
    ),
    path(
        "<course:course>/<instance:instance>/<sheet:sheet>/delete_section/<str:section>/",
        views.delete_section,
        name="delete_section"
    ),
    path(        "<course:course>/<instance:instance>/<sheet:sheet>/<bullet:target_bullet>/move/<str:placement>/",
        views.move_bullet,
        name="move_bullet"
    ),
    path(
        "<course:course>/<instance:instance>/<sheet:sheet>/<bullet:bullet>/edit/",
        views.edit_bullet,
        name="edit_bullet"
    ),
    path(
        "<course:course>/<instance:instance>/<sheet:sheet>/<bullet:bullet>/delete/",
        views.delete_bullet,
        name="delete_bullet"
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/",
        views.view_assessment,
        name="view_assessment"
    ),
    
]