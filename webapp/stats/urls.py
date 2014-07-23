from django.conf.urls import patterns, include, url

from . import views

urlpatterns = patterns(
    '',
    # For viewing task statistics
    url(r'^single-task/(?P<task_name>[^/]+)/$', views.single_task, name='single_task'),
    url(r'^users/(?P<training_name>[^/]+)/(?P<content_to_search>[^/]+)/(?P<year>\d{4})\-(?P<month>\d{2})\-(?P<day>\d{2})/$', views.course_users, name='course_users'),
    url(r'^all-tasks/(?P<course_name>[^/]+)/$', views.all_tasks, name='all_tasks'),
    url(r'^user-task/(?P<user_name>[^/]+)/(?P<task_name>.+)/$', views.user_task, name='user_task'),
)
