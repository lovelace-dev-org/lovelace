from django.conf.urls import patterns, include, url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    # TODO: redirect_to doesn't work anymore, serve favicon properly through a web server directive!
    #url(r'^favicon\.ico$', 'django.views.generic.simple.redirect_to', {'url': '/static/favicon.ico'}),

    # For the registration module
    # TODO: AllAuth
    #url(r'^accounts/', include('registration.urls')),
    #url(r'^accounts/', views.index),

    # For viewing and changing user information
    url(r'^answers/(?P<user>[^/]+)/(?P<course>[^/]+)/(?P<exercise>[^/]+)',
        views.show_answers, name='show_answers'),
    url(r'^user/(?P<user_name>[^/]+)/$', views.user),
    url(r'^profile/$', views.user_profile),
    url(r'^profile/save/$', views.user_profile_save),

    # For serving images
    # TODO: Serve directly from the web server
    #url(r'^media/images/(?P<imagename>.+)$', views.image_download),

    # For serving uploaded files
    # TODO: Noooo... Do it with the web server conf.
    #url(r'^media/files/(?P<filename>.+)$', views.file_download),
    #url(r'^media/(?P<filename>.+)$', views.file_download),

    # For calendar POST requests
    url(r'^calendar/(?P<calendar_id>\d+)/(?P<event_id>\d+)/$', views.calendar_post),

    # Sandbox: admin view & answer for content pages without saved results
    url(r'^sandbox/(?P<content_slug>[^/]+)/$', views.content, {'sandbox': True,}, name='sandbox',),

    # Course front page and content views
    url(r'^(?P<course_slug>[^/]+)/$', views.course, name='course'),
    url(r'^(?P<course_slug>[^/]+)/(?P<content_slug>[^/]+)/$', views.content, name='content'),

    # Exercise sending for checking, progress and evaluation views
    url(r'^(?P<course_slug>[^/]+)/(?P<content_slug>[^/]+)/check/$', views.check_answer, name='check'),
    url(r'^(?P<course_slug>[^/]+)/(?P<content_slug>[^/]+)/progress/(?P<task_id>[^/]+)/$',
        views.check_progress, name='check_progress'),
    url(r'^(?P<course_slug>[^/]+)/(?P<content_slug>[^/]+)/evaluation/(?P<task_id>[^/]+)/$',
        views.file_exercise_evaluation, name='file_exercise_evaluation'),
]

# For serving uploaded files on development server only:
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
