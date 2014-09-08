from django.conf.urls import patterns, include, url

from django.conf import settings # Bad style! This info is not actually needed!

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),

    # TODO: redirect_to doesn't work anymore, serve favicon properly through a web server directive!
    #url(r'^favicon\.ico$', 'django.views.generic.simple.redirect_to', {'url': '/static/favicon.ico'}),

    # For the registration module
    # TODO: AllAuth
    url(r'^accounts/', include('registration.urls')),
    url(r'^accounts/', 'courses.views.index'),

    # For viewing and changing user information
    url(r'^answers/(?P<user>[^/]+)/(?P<course>[^/]+)/(?P<task>[^/]+)',
        views.show_answers, name='show_answers'),
    url(r'^user/(?P<user_name>[^/]+)/$', 'courses.views.user'),
    url(r'^profile/$', 'courses.views.user_profile'),
    url(r'^profile/save/$', 'courses.views.user_profile_save'),

    # For serving images
    # TODO: Serve directly from the web server
    url(r'^media/images/(?P<imagename>.+)$', 'courses.views.image_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),

    # For calendar POST requests
    url(r'^calendar/(?P<calendar_id>\d+)/(?P<event_id>\d+)/$', 'courses.views.calendar_post'),

    # For serving uploaded files
    # TODO: Noooo... Do it with the web server conf.
    url(r'^media/files/(?P<filename>.+)$', 'courses.views.file_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),
    url(r'^media/(?P<filename>.+)$', 'courses.views.file_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),

    # Sandbox: admin view & answer for content pages without saved results
    url(r'^sandbox/(?P<content_name>[^/]+)/$', views.content,
        {'sandbox': True,},
        name='sandbox_content',),

    # Course front page, course graph and content views
    url(r'^(?P<training_name>[^/]+)/$', views.training,
        {'raippa_root': settings.BASE_DIR,
         'media_root': settings.MEDIA_ROOT,
         'media_url': settings.MEDIA_URL,},
        name='training'
       ),
    url(r'^(?P<training_name>[^/]+)/graph\.vg$', views.course_graph, name='course_graph'),
    url(r'^(?P<training_name>[^/]+)/(?P<content_name>[^/]+)/$', views.content,
        {'raippa_root': settings.BASE_DIR,
         'media_root': settings.MEDIA_ROOT,
         'media_url':settings.MEDIA_URL,},
        name='content'
       ),

    # Exercise sending for checking, progress and evaluation views
    url(r'^(?P<training_name>[^/]+)/(?P<content_name>[^/]+)/check/$', views.check_answer,
        {'media_root': settings.MEDIA_ROOT,
         'media_url':settings.MEDIA_URL,}
       ),
    url(r'^(?P<course_name>[^/]+)/(?P<content_name>[^/]+)/progress/(?P<task_id>[^/]+)/$',
        views.check_progress, name='check_progress'),
    url(r'^(?P<course_name>[^/]+)/(?P<content_name>[^/]+)/evaluation/(?P<task_id>[^/]+)/$',
        views.file_exercise_evaluation, name='file_exercise_evaluation'),
)
