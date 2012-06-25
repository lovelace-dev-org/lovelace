from django.conf.urls import patterns, include, url

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

#courses_name = "training" # courses

urlpatterns = patterns('',
    url(r'^$', 'courses.views.index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('registration.urls')),
    url(r'^accounts/', 'courses.views.index'),
    url(r'^user/(?P<user_name>[^/]+)/$', 'courses.views.user'),
    url(r'^media/(?P<filename>.+)$', 'courses.views.file_download', {'media_root': settings.MEDIA_ROOT,}),
    url(r'^(?P<training_name>[^/]+)/$', 'courses.views.training', {'media_root': settings.MEDIA_ROOT, 'media_url':settings.MEDIA_URL,}),
    url(r'^(?P<training_name>[^/]+)/graph\.vg$', 'courses.views.course_graph'),
    url(r'^(?P<training_name>[^/]+)/(?P<content_name>[^/]+)/$', 'courses.views.content', {'media_root': settings.MEDIA_ROOT, 'media_url':settings.MEDIA_URL,}),

    # Examples:
    # url(r'^$', 'raippa.views.home', name='home'),
    # url(r'^raippa/', include('raippa.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
)
