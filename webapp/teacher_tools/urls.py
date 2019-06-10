from django.urls import path

from . import views
app_name = "teacher_tools"

urlpatterns = [
    path("<course:course>/<instance:instance>/<content:content>/download_answers/", views.download_answers, name="download_answers"),
    path("<course:course>/<instance:instance>/enrollments/", views.manage_enrollments, name="manage_enrollments"),
    path("<course:course>/<instance:instance>/completion/<user:user>/", views.student_course_completion, name="student_completion"),
    path("<course:course>/<instance:instance>/completion/", views.course_completion, name="completion"),
    path("<course:course>/<instance:instance>/completion-csv/", views.course_completion_csv, name="completion_csv"),
    path("<course:course>/<instance:instance>/completion-csv/progress/<slug:task_id>/", views.course_completion_csv_progress, name="completion_csv_progress"),
    path("<course:course>/<instance:instance>/completion-csv/download/<slug:task_id>/", views.course_completion_csv_download, name="completion_csv_download"),
    path("<course:course>/<instance:instance>/reminders/load/", views.load_reminders, name="load_reminders"),
    path("<course:course>/<instance:instance>/reminders/discard/", views.discard_reminders, name="discard_reminders"),
    path("<course:course>/<instance:instance>/reminders/progress/<slug:task_id>/", views.reminders_progress, name="reminders_progress"),
    path("<course:course>/<instance:instance>/reminders/", views.manage_reminders, name="reminders"),
    path("<course:course>/<instance:instance>/<content:content>/plagiarism/", views.exercise_plagiarism, name="exercise_plagiarism"),
]

