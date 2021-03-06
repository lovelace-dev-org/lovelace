from django.conf.urls import include, url
from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),

    # For viewing and changing user information
    path("answers/<user:user>/<course:course>/<instance:instance>/<content:exercise>/<answer:answer>/",
        views.get_file_exercise_evaluation, name="get_file_exercise_evaluation"),
    path("answers/<user:user>/<course:course>/<instance:instance>/<content:exercise>/",
        views.show_answers, name="show_answers"),
    path("answers/<user:user>/<course:course>/<instance:instance>/<answer:answer>/<str:filename>/show/",
         views.show_answer_file_content, name="show_answer_file"),
    path("user/<user:user>/", views.user),
    path("profile/", views.user_profile),
    path("profile/save/", views.user_profile_save),

    # For calendar POST requests
    path("calendar/<int:calendar_id>/<int:event_id>/", views.calendar_post, name="calendar_post",),

    # Sandbox: admin view & answer for content pages without saved results
    # currently disabled
    # path("sandbox/<content:content>/", views.sandboxed_content, name="sandbox",),
    # path("sandbox/<content:content>/check_sandboxed/", views.check_answer_sandboxed, name="check_sandboxed"),
    
    # Help pages
    path("help/", views.help_list, name="help_list",),
    path("help/markup/", views.markup_help, name="markup_help",),
    path("terms/", views.terms, name="terms",),

    # Enrollment views
    path("enroll/<course:course>/<instance:instance>/", views.enroll, name="enroll"),
    path("withdraw/<course:course>/<instance:instance>/", views.withdraw, name="withdraw"),
    
    # Course front page and content views
    path("answers/<user:user>/<course:course>/<instance:instance>/<answer:answer>/<str:filename>/download/", views.download_answer_file, name="download_answer_file"),
    path("<course:course>/", views.course_instances, name="course_instances"),
    path("<course:course>/<instance:instance>/", views.course, name="course"),
    path("<course:course>/<instance:instance>/<content:content>/", views.content, name="content"),

    # Download views
    path("file-download/embedded/<course:course>/<instance:instance>/<file:mediafile>/", views.download_embedded_file, name="download_embedded_file"),
    url(r"^file-download/media/(?P<file_slug>[^/]+)/(?P<field_name>[^/]+)/$", views.download_media_file, name="download_media_file"),
    url(r"^file-download/template-backend/(?P<exercise_id>\d+)/(?P<filename>[^/]+)/$",
        views.download_template_exercise_backend, name="download_template_exercise_backend"),


    # Exercise sending for checking, progress and evaluation views
    path("<course:course>/<instance:instance>/<content:content>/<revision:revision>/check/", views.check_answer, name="check"),
    path("<course:course>/<instance:instance>/<content:content>/<revision:revision>/exercise-session/", views.get_repeated_template_session, name="get_repeated_template_session"),
    path("<course:course>/<instance:instance>/<content:content>/<revision:revision>/progress/<slug:task_id>/",
        views.check_progress, name="check_progress"),
    path("<course:course>/<instance:instance>/<content:content>/<revision:revision>/evaluation/<slug:task_id>/",
        views.file_exercise_evaluation, name="file_exercise_evaluation"),
]

# For serving uploaded files on development server only:
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
