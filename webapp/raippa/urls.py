from django.conf.urls import patterns, include, url
from django.contrib import admin

# TODO: Design the url hierarchy from scratch
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^stats/', include('stats.urls', namespace='stats')),
    url(r'^feedback/', include('feedback.urls', namespace='feedback')),
    url(r'^', include('courses.urls', namespace='courses')),
]
