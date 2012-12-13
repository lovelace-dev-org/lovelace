from django.conf.urls import patterns, include, url

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

#courses_name = "training" # courses

urlpatterns = patterns(
    '',
    url(r'^$', 'courses.views.index'),
    url(r'^favicon\.ico$', 'django.views.generic.simple.redirect_to', {'url': '/static/favicon.ico'}),

    # The admin site
    url(r'^admin/', include(admin.site.urls)),

    # For the registration module
    url(r'^accounts/', include('registration.urls')),
    url(r'^accounts/', 'courses.views.index'),

    # For viewing and changing user information
    url(r'^user/(?P<user_name>[^/]+)/$', 'courses.views.user'),
    url(r'^profile/$', 'courses.views.user_profile'),
    url(r'^profile/save/$', 'courses.views.user_profile_save'),

    # For viewing task statistics
    url(r'^stats/(?P<task_name>[^/]+)/$', 'courses.views.stats'),
    url(r'^users/(?P<training_name>[^/]+)/$', 'courses.views.users'),
    url(r'^allstats/(?P<course_name>[^/]+)/$', 'courses.views.all_task_stats'),

    url(r'^usertask/(?P<user_name>[^/]+)/(?P<task_name>.+)/$', 'courses.views.user_task_stats'),

    # For serving images
    url(r'^media/images/(?P<imagename>.+)$', 'courses.views.image_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),

    # For calendar POST requests
    url(r'^calendar/(?P<calendar_id>\d+)/(?P<event_id>\d+)/$', 'courses.views.calendar_post'),

    # For serving uploaded files
    url(r'^media/files/(?P<filename>.+)$', 'courses.views.file_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),
    url(r'^media/(?P<filename>.+)$', 'courses.views.file_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),

    # Course front page, course graph and content views
    url(r'^(?P<training_name>[^/]+)/$', 'courses.views.training',
        {'raippa_root': settings.RAIPPA_ROOT,
         'media_root': settings.MEDIA_ROOT,
         'media_url': settings.MEDIA_URL,}
       ),
    url(r'^(?P<training_name>[^/]+)/graph\.vg$', 'courses.views.course_graph'),
    url(r'^(?P<training_name>[^/]+)/(?P<content_name>[^/]+)/$', 'courses.views.content',
        {'raippa_root': settings.RAIPPA_ROOT,
         'media_root': settings.MEDIA_ROOT,
         'media_url':settings.MEDIA_URL,}
       ),
    url(r'^(?P<training_name>[^/]+)/(?P<content_name>[^/]+)/check/$', 'courses.views.check_answer',
        {'media_root': settings.MEDIA_ROOT,
         'media_url':settings.MEDIA_URL,}
       ),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
)
