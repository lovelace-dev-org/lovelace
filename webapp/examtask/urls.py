from django.urls import path
from utils.converters import register_model_converter

from . import models, views

register_model_converter(models.ExamTaskAttempt, name="taskattempt")

app_name = "examtask"

urlpatterns = [
    path(
        "<course:course>/<instance:instance>/<content:parent>/<content:content>/settings/",
        views.exam_task_settings,
        name="exam_task_settings",
    ),
    path(
        "<course:course>/<instance:instance>/<content:parent>/<content:content>/attempts/",
        views.exam_task_attempts,
        name="exam_task_attempts",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/attempts/add/",
        views.add_task_attempt,
        name="add_task_attempt",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/"
        "attempts/<taskattempt:attempt>/edit/",
        views.edit_task_attempt,
        name="edit_task_attempt",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/"
        "attempts/<taskattempt:attempt>/delete/",
        views.delete_task_attempt,
        name="delete_task_attempt",
    ),
]
