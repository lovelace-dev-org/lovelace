from django.conf.urls import patterns, include, url
from django.contrib import admin

# TODO: Design the url hierarchy from scratch
urlpatterns = patterns(
    '',
    url(r'^', include('courses.urls', namespace='courses')),
    url(r'^admin/', include(admin.site.urls)),
)
