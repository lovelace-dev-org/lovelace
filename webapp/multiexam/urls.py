from django.urls import path
from model_path_converter import register_model_converter

from . import views, models

app_name = "multiexam"

register_model_converter(models.MultipleQuestionExamAttempt, name="attempt")


urlpatterns = [
    path(
        "<course:course>/<instance:instance>/<content:content>/",
        views.get_exam_attempt,
        name="get_exam_attempt",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/attempts/",
        views.manage_attempts,
        name="manage_attempts",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/open_attempt/",
        views.open_new_attempt,
        name="open_attempt",
    ),

    # attempt management

    path(
        "<course:course>/<instance:instance>/<attempt:attempt>/preview/",
        views.preview_attempt,
        name="preview_attempt",
    ),
    path(
        "<course:course>/<instance:instance>/<attempt:attempt>/settings/",
        views.attempt_settings,
        name="attempt_settings",
    ),
    path(
        "<course:course>/<instance:instance>/<attempt:attempt>/delete/",
        views.delete_attempt,
        name="delete_attempt",
    ),

    # other

    path(
        "file-download/multiexam/<int:exercise_id>/<str:field_name>/<str:filename>/",
        views.download_question_pool,
        name="download_question_pool",
    )
]
