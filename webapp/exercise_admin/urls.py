from django.urls import path

from . import views

app_name = "exercise_admin"

urlpatterns = [
    path("", views.index, name="index"),
    ## For administration (add/edit) of file upload exercises
    path("file-upload/add/", views.file_upload_exercise, {"action": "add"}, name="file_upload_add"),
    path(
        "file-upload/<int:exercise_id>/change/",
        views.file_upload_exercise,
        {"action": "change"},
        name="file_upload_change",
    ),
    path(
        "file-download/exercise/<int:exercise_id>/<int:file_id>/<str:lang_code>/",
        views.download_exercise_file,
        name="download_exercise_file",
    ),
    path(
        "file-download/instance/<str:file_id>/<str:lang_code>/",
        views.download_instance_file,
        name="download_instance_file",
    ),
    # File upload exercise related objects
    path("instance-files/", views.get_instance_files, name="get_instance_files"),
    path("instance_files/edit/", views.edit_instance_files, name="edit_instance_files"),
    path("feedback-questions/", views.get_feedback_questions, name="get_feedback_questions"),
    path("feedback-questions/edit/", views.edit_feedback_questions, name="edit_feedback_questions"),
]
