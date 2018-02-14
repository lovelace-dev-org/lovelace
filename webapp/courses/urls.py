from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),

    # For viewing and changing user information
    url(r'^answers/(?P<user>[^/]+)/(?P<answer_id>\d+)$',
        views.get_file_exercise_evaluation, name='get_file_exercise_evaluation'),
    url(r'^answers/(?P<user>[^/]+)/(?P<course>[^/]+)/(?P<instance>[^/]+)/(?P<answer_id>\d+)/(?P<filename>[^/]+)/download/$', views.download_answer_file, name='download_answer_file'),
    url(r'^answers/(?P<user>[^/]+)/(?P<course>[^/]+)/(?P<instance>[^/]+)/(?P<exercise>[^/]+)',
        views.show_answers, name='show_answers'),
    url(r'^user/(?P<user_name>[^/]+)/$', views.user),
    url(r'^profile/$', views.user_profile),
    url(r'^profile/save/$', views.user_profile_save),

    # For calendar POST requests
    url(r'^calendar/(?P<calendar_id>\d+)/(?P<event_id>\d+)/$', views.calendar_post, name='calendar_post',),

    # Sandbox: admin view & answer for content pages without saved results
    url(r'^sandbox/(?P<content_slug>[^/]+)/$', views.sandboxed_content, name='sandbox',),
    url(r'^sandbox/(?P<content_slug>[^/]+)/check_sandboxed/$', views.check_answer_sandboxed, name='check_sandboxed'),
    
    # Help pages
    url(r'^help/$', views.help_list, name='help_list',),
    url(r'^help/markup/$', views.markup_help, name='markup_help',),
    url(r'^terms/$', views.terms, name='terms',),

    # Course front page and content views
    url(r'^(?P<course_slug>[^/]+)/$', views.course_instances, name='course_instances'),
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/$', views.course, name='course'),
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/$', views.content, name='content'),

    url(r'^file-download/embedded/(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<file_slug>[^/]+)/$', views.download_embedded_file, name='download_embedded_file'),
    url(r'^file-download/media/(?P<instance_id>\d+)/(?P<file_slug>[^/]+)/(?P<field_name>[^/]+)/$', views.download_media_file, name='download_media_file'),
    url(r'^file-download/template-backend/(?P<exercise_id>\d+)/(?P<filename>[^/]+)/$',
        views.download_template_exercise_backend, name="download_template_exercise_backend"),

    # Exercise sending for checking, progress and evaluation views
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/(?P<revision>(?:\d+|head))/check/$', views.check_answer, name='check'),
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/(?P<revision>(?:\d+|head))/exercise-session/$', views.get_repeated_template_session, name='get_repeated_template_session'),
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/(?P<revision>(?:\d+|head))/progress/(?P<task_id>[^/]+)/$',
        views.check_progress, name='check_progress'),
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/(?P<revision>(?:\d+|head))/evaluation/(?P<task_id>[^/]+)/$',
        views.file_exercise_evaluation, name='file_exercise_evaluation'),
]

# For serving uploaded files on development server only:
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
