from django.conf.urls import patterns, include, url

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

#courses_name = "training" # courses

urlpatterns = patterns('',
    url(r'^$', 'courses.views.index'),

    # The admin site
    url(r'^admin/', include(admin.site.urls)),

    # For the registration module
    url(r'^accounts/', include('registration.urls')),
    url(r'^accounts/', 'courses.views.index'),

    # For viewing user information
    url(r'^user/(?P<user_name>[^/]+)/$', 'courses.views.user'),

    # For viewing task statistics
    url(r'^stats/(?P<task_name>[^/]+)/$', 'courses.views.stats'),

    # For serving uploaded files
    url(r'^media/(?P<filename>.+)$', 'courses.views.file_download',
        {'media_root': settings.MEDIA_ROOT,}
       ),

    # Course front page, course graph and content views
    url(r'^(?P<training_name>[^/]+)/$', 'courses.views.training',
        {'media_root': settings.MEDIA_ROOT,
         'media_url': settings.MEDIA_URL,}
       ),
    url(r'^(?P<training_name>[^/]+)/graph\.vg$', 'courses.views.course_graph'),
    url(r'^(?P<training_name>[^/]+)/(?P<content_name>[^/]+)/$', 'courses.views.content',
        {'media_root': settings.MEDIA_ROOT,
         'media_url':settings.MEDIA_URL,}
       ),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
)
