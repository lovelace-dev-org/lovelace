from django.urls import path
from utils.converters import register_model_converter

from . import views
from .models import ContentFeedbackQuestion

app_name = "feedback"

urlpatterns = [
    path(
        "statistics/<instance:instance>/<content:content>/",
        views.content_feedback_stats,
        name="statistics",
    ),
    path(
        "<instance:instance>/<content:content>/<feedback:question>/receive/",
        views.receive,
        name="receive",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/feedback/manage/",
        views.feedback_management_panel,
        name="feedback_management",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/feedback/edit/",
        views.edit_content_feedback,
        name="edit_content_feedback",
    ),
    path(
        "<course:course>/<instance:instance>/feedback/create/",
        views.create_feedback_question,
        name="create_feedback_question",
    ),
    path(
        "<course:course>/<instance:instance>/feedback/edit/<feedback:question>/",
        views.edit_feedback_question,
        name="edit_feedback_question",
    ),
    path(
        "<course:course>/<instance:instance>/feedback/delete/<feedback:question>/",
        views.delete_feedback_question,
        name="delete_feedback_question",
    ),
]
