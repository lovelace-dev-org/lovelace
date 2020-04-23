from django.urls import path

from . import views
app_name = "routine_exercise"

urlpatterns = [
    path(
        "<course:course>/<instance:instance>/<content:content>/<revision:revision>/routine-question/",
        views.get_routine_question,
        name="get_routine_question"
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/routine-progress/<slug:task_id>",
        views.routine_progress,
        name="task_progress"
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/<revision:revision>/routine-check/",
        views.check_routine_question,
        name="check_routine_question"
    ),
]

