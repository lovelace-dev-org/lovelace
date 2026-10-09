from django.urls import path

from . import views

app_name = "routine_exercise"

urlpatterns = [
    path(
        "<course:course>/<instance:instance>/<content:parent>/<content:content>"
        "/routine-question/",
        views.get_routine_question,
        name="get_routine_question",
    ),
    path(
        "<course:course>/<instance:instance>/<content:parent>/<content:content>/routine-progress/<slug:task_id>",
        views.routine_progress,
        name="task_progress",
    ),
    path(
        "<course:course>/<instance:instance>/<content:parent>/<content:content>/routine-check/",
        views.check_routine_question,
        name="check_routine_question",
    ),
    path(
        "file-download/routine-backend/<int:exercise_id>/<str:field_name>/<str:filename>/",
        views.download_routine_exercise_backend,
        name="download_routine_exercise_backend",
    ),

    # MANAGEMENT


    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "backend/",
        views.routine_backend_panel,
        name="routine_backend_panel",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "backend/<str:filename>/edit/",
        views.edit_backend,
        name="edit_backend",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "backend/<str:filename>/delete/",
        views.delete_backend,
        name="delete_backend",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "backend/add/",
        views.add_backend,
        name="add_backend",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "command/edit",
        views.edit_command,
        name="edit_command",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "template/",
        views.routine_template_panel,
        name="routine_template_panel",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "template/<int:qc>/<int:variant>/edit/",
        views.edit_template,
        name="edit_template",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "template/<int:qc>/<int:variant>/delete/",
        views.delete_template,
        name="delete_template",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/"
        "template/<int:qc>/add/",
        views.add_template,
        name="add_template",
    ),



]
