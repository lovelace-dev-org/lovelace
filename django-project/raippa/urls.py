from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^courses/$', 'courses.views.index'),
    url(r'^courses/(?P<course_name>.+)/$', 'courses.views.course'),
    url(r'^courses/(?P<course_name>.+)/(?P<incarnation_name>.+)/$', 'courses.views.incarnation'),
    url(r'^courses/(?P<course_name>.+)/(?P<incarnation_name>.+)/(?P<content_name>.+)/$', 'courses.views.content'),
    # Examples:
    # url(r'^$', 'raippa.views.home', name='home'),
    # url(r'^raippa/', include('raippa.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
