from django.urls import path

from . import views

app_name = "answerless"

urlpatterns = [
    path(
        "<course:course>/<instance:instance>/<content:parent>/<content:content>/add/",
        views.add_student_entry,
        name="add_student_entry",
    ),
]
