from django.conf.urls import patterns, include, url

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

courses_name = "training" # courses

urlpatterns = patterns('',
    url(r'^%s/$' % courses_name, 'courses.views.index'),
    url(r'^%s/(?P<course_name>[^/]+)/$' % courses_name, 'courses.views.course'),
    url(r'^%s/(?P<course_name>[^/]+)/(?P<incarnation_name>[^/]+)/$' % courses_name, 'courses.views.incarnation'),
    url(r'^%s/(?P<course_name>[^/]+)/(?P<incarnation_name>[^/]+)/(?P<content_name>[^/]+)/$' % courses_name, 'courses.views.content', {'media_root': settings.MEDIA_ROOT,}),

    url(r'^media/(?P<course_name>[^/]+)/(?P<filename>.+)$', 'courses.views.file_download', {'media_root': settings.MEDIA_ROOT,}),
    # Examples:
    # url(r'^$', 'raippa.views.home', name='home'),
    # url(r'^raippa/', include('raippa.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
